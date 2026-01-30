import os
import zipfile
import logging
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Configuração de logging para monitoramento do pipeline
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataTransformation:
    # Pipeline de transformação e enriquecimento de dados com validação híbrida

    # URLs para busca do cadastro de operadoras da ANS
    BASE_URL_CADASTRO_COMPLETO = "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude/"
    BASE_URL_CADASTRO_ATIVAS = "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/"
    
    def __init__(self, csv_consolidado_path):
        # Inicializa caminhos e garante a existência dos diretórios necessários
        self.csv_consolidado = Path(csv_consolidado_path)
        self.output_dir = Path("output")
        self.temp_dir = Path("temp")
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        if not self.csv_consolidado.exists():
            raise FileNotFoundError(f"Arquivo consolidado não encontrado: {csv_consolidado_path}")
    
    def calcular_digito_verificador_cnpj(self, cnpj_base):
        # Implementa o algoritmo oficial da Receita Federal para validação de CNPJ
        if len(str(cnpj_base)) != 12 or not str(cnpj_base).isdigit():
            return None
            
        def obter_digito(base, multiplicadores):
            # Cálculo do dígito verificador com base nos multiplicadores fornecidos
            soma = sum(int(base[i]) * multiplicadores[i] for i in range(len(base)))
            resto = soma % 11
            return 0 if resto < 2 else 11 - resto
        
        multiplicadores_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        multiplicadores_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        
        d1 = obter_digito(str(cnpj_base), multiplicadores_1)
        d2 = obter_digito(str(cnpj_base) + str(d1), multiplicadores_2)
        
        return str(d1) + str(d2)
    
    def validar_cnpj(self, cnpj):
        # Validação híbrida: suporta Registro ANS (6 dígitos) e CNPJ (14 dígitos)
        if pd.isna(cnpj) or str(cnpj).strip() == '':
            return False, 'CNPJ_VAZIO'
        
        cnpj_limpo = ''.join(c for c in str(cnpj) if c.isdigit())

        # Identifica se é um Registro ANS válido (comum nos dados da ANS)
        if len(cnpj_limpo) == 6:
            return True, 'REGISTRO_ANS_VALIDO'
        
        if len(cnpj_limpo) != 14:
            return False, 'CNPJ_TAMANHO_INVALIDO'
        
        if len(set(cnpj_limpo)) == 1:
            return False, 'CNPJ_DIGITOS_REPETIDOS'
        
        base = cnpj_limpo[:12]
        digitos_informados = cnpj_limpo[12:14]
        digitos_calculados = self.calcular_digito_verificador_cnpj(base)
        
        if digitos_calculados != digitos_informados:
            return False, 'CNPJ_DV_INVALIDO'
        
        return True, 'CNPJ_VALIDO'
    
    def validar_dados(self, df):
        # Executa validações vetorizadas e otimização de tipos para grandes volumes
        logger.info("Aplicando validações de dados e otimização de memória...")
        
        df = df.copy()
        
        # Verifica presença de colunas vitais para o processamento
        cols_obrigatorias = ['CNPJ', 'RazaoSocial', 'ValorDespesas']
        if not all(c in df.columns for c in cols_obrigatorias):
            raise KeyError(f"Colunas obrigatórias ausentes: {cols_obrigatorias}")
        
        # Otimiza colunas de baixa cardinalidade para reduzir uso de RAM
        for col in ['Trimestre', 'Ano']:
            if col in df.columns:
                df[col] = df[col].astype('category')
        
        # Validação de valores com máscara para evitar warnings de comparação com NaN
        df['ValidacaoValor'] = 'VALOR_VALIDO'
        mask_nulo = pd.isna(df['ValorDespesas'])
        df.loc[mask_nulo, 'ValidacaoValor'] = 'VALOR_NULO'
        df.loc[~mask_nulo & (df['ValorDespesas'] <= 0), 'ValidacaoValor'] = 'VALOR_NAO_POSITIVO'
        
        # Validação de integridade da Razão Social
        df['ValidacaoRazao'] = 'RAZAO_VALIDA'
        razao_str = df['RazaoSocial'].astype(str)
        df.loc[df['RazaoSocial'].isna() | (razao_str.str.strip() == '') | (razao_str.str.lower() == 'nan'), 'ValidacaoRazao'] = 'RAZAO_VAZIA'
        df.loc[df['RazaoSocial'].isin(['N/A']), 'ValidacaoRazao'] = 'RAZAO_NAO_DISPONIVEL'
        
        # Validação de CNPJ otimizada por valores únicos (performance para 2M+ registros)
        cnpj_unicos = df['CNPJ'].dropna().unique()
        mapa_validacao = {cnpj: self.validar_cnpj(cnpj)[1] for cnpj in cnpj_unicos}
        df['ValidacaoCNPJ'] = df['CNPJ'].map(mapa_validacao).fillna('CNPJ_VAZIO')
        
        return df
        
    def baixar_dados_cadastrais(self):
        # Web scraping para obter o cadastro atualizado da ANS
        logger.info("Buscando cadastro de operadoras da ANS...")
        
        # Limite de tamanho para evitar downloads excessivos
        MAX_DOWNLOAD_SIZE = 150 * 1024 * 1024 
        
        for tentativa, url_base in enumerate([self.BASE_URL_CADASTRO_COMPLETO, self.BASE_URL_CADASTRO_ATIVAS], 1):
            try:
                response = requests.get(url_base, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                csv_files = [urljoin(url_base, link['href']) for link in soup.find_all('a', href=True) if link['href'].endswith('.csv')]
                
                if csv_files:
                    url_completa = csv_files[-1] 
                    logger.info(f"Baixando: {url_completa.split('/')[-1]}")
                    
                    with requests.get(url_completa, stream=True, timeout=120) as r:
                        r.raise_for_status()
                        
                        downloaded = 0
                        local_path = self.temp_dir / "operadoras_cadastro.csv"
                        with open(local_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if chunk:
                                    downloaded += len(chunk)
                                    if downloaded > MAX_DOWNLOAD_SIZE:
                                        raise ValueError("O arquivo excede o limite de tamanho permitido.")
                                    f.write(chunk)
                    return local_path
            except Exception as e:
                logger.warning(f"Falha na tentativa {tentativa}: {e}")
                continue
        return None
    
    def ler_dados_cadastrais(self, arquivo_path):
        # Carregamento resiliente do arquivo cadastral
        logger.info("Lendo dados cadastrais...")
        for encoding in ['utf-8', 'iso-8859-1', 'cp1252']:
            for sep in [';', ',', '\t']:
                try:
                    df = pd.read_csv(arquivo_path, sep=sep, encoding=encoding, low_memory=False, dtype=str)
                    if len(df.columns) > 1:
                        return df
                except Exception:
                    continue
        raise Exception("Erro ao ler arquivo cadastral.")
    
    def enriquecer_dados(self, df_consolidado, df_cadastro):
        # Join inteligente priorizando Registro ANS para maximizar o match
        logger.info("Enriquecendo dados com informações cadastrais...")
        df_cadastro.columns = df_cadastro.columns.str.strip().str.upper()
        
        col_cnpj = next((c for c in df_cadastro.columns if 'CNPJ' in c), None)
        col_registro = next((c for c in df_cadastro.columns if c == 'REGISTRO_OPERADORA'), None)
        col_razao = next((c for c in df_cadastro.columns if c == 'RAZAO_SOCIAL'), None)
        col_uf = next((c for c in df_cadastro.columns if c in ['UF', 'SIGLA_UF']), None)
        
        # Define a chave de join baseada na disponibilidade do cadastro
        chave_join = 'REGISTRO_ANS' if col_registro else 'CNPJ'
        renomear = {col_registro if col_registro else col_cnpj: 'ChaveJoin'}
        if col_razao: renomear[col_razao] = 'RazaoSocialCadastro'
        if col_uf: renomear[col_uf] = 'UF'
        
        df_cad_slim = df_cadastro[list(renomear.keys())].rename(columns=renomear).copy()
        df_cad_slim['ChaveJoin'] = df_cad_slim['ChaveJoin'].astype(str).str.replace(r'\D', '', regex=True)
        df_cad_slim = df_cad_slim.drop_duplicates('ChaveJoin')
        
        df_enriquecido = df_consolidado.copy()
        df_enriquecido['ChaveJoin'] = df_enriquecido['CNPJ']
        
        df_final = df_enriquecido.merge(df_cad_slim, on='ChaveJoin', how='left', indicator=True)
        
        # Atualiza a Razão Social apenas onde estava vazia ou N/A
        if 'RazaoSocialCadastro' in df_final.columns:
            mask = (df_final['RazaoSocial'].isin(['N/A', '']) | df_final['RazaoSocial'].isna()) & df_final['RazaoSocialCadastro'].notna()
            df_final.loc[mask, 'RazaoSocial'] = df_final.loc[mask, 'RazaoSocialCadastro']
            df_final.drop(columns=['RazaoSocialCadastro'], inplace=True)

        df_final['StatusEnriquecimento'] = np.where(df_final['_merge'] == 'both', 'ENRIQUECIDO', 'SEM_CADASTRO')
        df_final['UF'] = df_final['UF'].fillna('XX')
        return df_final.drop(columns=['ChaveJoin', '_merge'])
        
    def agregar_dados(self, df):
        # Gera o arquivo final com métricas estatísticas (Total, Média e Desvio Padrão)
        logger.info("Agregando dados por Razão Social e UF...")
        
        df_v = df[(df['ValidacaoCNPJ'].isin(['CNPJ_VALIDO', 'REGISTRO_ANS_VALIDO'])) & (df['ValidacaoValor'] == 'VALOR_VALIDO')].copy()
        df_v = df_v[~df_v['RazaoSocial'].isin(['N/A', '', 'nan']) & df_v['RazaoSocial'].notna()]
        
        if df_v.empty: return pd.DataFrame()
        
        # Agrupamento otimizado com nomeação direta de colunas
        agregado = df_v.groupby(['RazaoSocial', 'UF'], observed=True).agg(
            TotalDespesas=('ValorDespesas', 'sum'),
            MediaDespesas=('ValorDespesas', 'mean'),
            DesvioPadrao=('ValorDespesas', 'std'),
            QtdRegistros=('ValorDespesas', 'count')
        ).reset_index().fillna(0)
        
        return agregado.sort_values('TotalDespesas', ascending=False)
        
    def executar(self):
        # Orquestração de todas as etapas do pipeline
        logger.info("="*60)
        logger.info("TESTE 2 - TRANSFORMAÇÃO E VALIDAÇÃO DE DADOS")
        logger.info("="*60)
        
        try:
            df = pd.read_csv(self.csv_consolidado, dtype={'CNPJ': str, 'RazaoSocial': str})
            
            df_validado = self.validar_dados(df)
            df_validado.to_csv(self.output_dir / "dados_validados.csv", index=False)
            
            cadastro = self.baixar_dados_cadastrais()
            df_enriquecido = self.enriquecer_dados(df_validado, self.ler_dados_cadastrais(cadastro)) if cadastro else df_validado
            df_enriquecido.to_csv(self.output_dir / "dados_enriquecidos.csv", index=False)
            
            df_agregado = self.agregar_dados(df_enriquecido)
            df_agregado.to_csv(self.output_dir / "despesas_agregadas.csv", index=False)
            
            self.gerar_relatorio(df_validado, df_enriquecido, df_agregado)
            self.compactar_resultado()
            
            # Limpeza de arquivos temporários para higiene do ambiente
            for f in self.temp_dir.glob('*'): f.unlink()
            
            logger.info("\n✓ TESTE 2 CONCLUÍDO COM SUCESSO!")
        except Exception as e:
            logger.error(f"Erro fatal no pipeline: {e}")

    def gerar_relatorio(self, df_v, df_e, df_a):
        # Gera relatório TXT com análise de integridade
        with open(self.output_dir / "relatorio_teste2.txt", 'w', encoding='utf-8') as f:
            f.write(f"RELATÓRIO TESTE 2\nTotal Registros: {len(df_v)}\n\n")
            f.write(f"VALIDAÇÃO CNPJ:\n{df_v['ValidacaoCNPJ'].value_counts().to_string()}\n\n")
            f.write(f"ENRIQUECIMENTO:\n{df_e['StatusEnriquecimento'].value_counts().to_string()}\n\n")
            f.write(f"AGREGAÇÃO:\nTotal Grupos: {len(df_a)}\n")
            if not df_a.empty: f.write(f"\nTop 10:\n{df_a.head(10).to_string(index=False)}")

    def compactar_resultado(self):
        # Gera o pacote ZIP final para entrega conforme requisito
        zip_path = self.output_dir / "Teste_Mauricio_Alves.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in self.output_dir.glob('*.*'):
                if f.suffix in ['.csv', '.txt']: zipf.write(f, f.name)

if __name__ == "__main__":
    # Detecção automática de caminhos (Docker vs Local)
    caminhos = ['/app/input/consolidado_despesas.csv', '../Teste1_ANS_Integration/output/consolidado_despesas.csv', 'output/consolidado_despesas.csv']
    csv_path = next((p for p in caminhos if os.path.exists(p)), 'output/consolidado_despesas.csv')
    
    DataTransformation(csv_path).executar()
    
import os
import zipfile
import logging
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Configuração de logging para monitoramento detalhado do pipeline
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataTransformation:
    # Pipeline profissional de transformação e enriquecimento de dados da ANS

    # Limite máximo de download para evitar ataques DoS
    MAX_DOWNLOAD_SIZE = 150 * 1024 * 1024
    
    # URLs oficiais para busca do cadastro de operadoras
    BASE_URL_CADASTRO_COMPLETO = "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude/"
    BASE_URL_CADASTRO_ATIVAS = "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/"
    
    def __init__(self, csv_consolidado_path):
        # Inicializa diretórios e caminhos, validando a existência do arquivo de entrada
        self.csv_consolidado = Path(csv_consolidado_path)
        self.output_dir = Path("output")
        self.temp_dir = Path("temp")
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        if not self.csv_consolidado.exists():
            raise FileNotFoundError(f"Arquivo de entrada não encontrado: {csv_consolidado_path}")

    def calcular_digito_verificador_cnpj(self, cnpj_base):
        # Implementa o algoritmo oficial de dígitos verificadores do CNPJ
        cnpj_str = str(cnpj_base)
        if len(cnpj_str) != 12 or not cnpj_str.isdigit():
            return None
            
        def obter_digito(base, multiplicadores):
            soma = sum(int(base[i]) * multiplicadores[i] for i in range(len(base)))
            resto = soma % 11
            return 0 if resto < 2 else 11 - resto
        
        first_digit_multiplier = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        second_digit_multiplier = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        
        d1 = obter_digito(cnpj_str, first_digit_multiplier)
        d2 = obter_digito(cnpj_str + str(d1), second_digit_multiplier)
        
        return str(d1) + str(d2)

    def validar_cnpj(self, cnpj):
        # Validação híbrida: Registro ANS (6 dígitos) ou CNPJ (14 dígitos)
        if pd.isna(cnpj) or str(cnpj).strip() == '':
            return False, 'CNPJ_VAZIO'
        
        cnpj_limpo = ''.join(c for c in str(cnpj) if c.isdigit())

        # Aceita Registro ANS baseado em tamanho e composição numérica
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
        # Executa validações vetorizadas e otimiza performance processando valores únicos
        logger.info("Aplicando validações de dados e otimização de memória...")
        df = df.copy()
        
        # Verificação rigorosa de colunas obrigatórias
        cols_req = ['CNPJ', 'RazaoSocial', 'ValorDespesas']
        colunas_ausentes = [c for c in cols_req if c not in df.columns]
        if colunas_ausentes:
            raise KeyError(f"Colunas ausentes: {colunas_ausentes}. Esperadas: {cols_req}")
        
        for col in ['Trimestre', 'Ano']:
            if col in df.columns:
                df[col] = df[col].astype('category')
        
        # Conversão e validação de valores financeiros (evita warnings com NaN)
        df['ValorDespesas'] = pd.to_numeric(df['ValorDespesas'], errors='coerce')
        df['ValidacaoValor'] = 'VALOR_VALIDO'
        mask_valor_nulo = pd.isna(df['ValorDespesas'])
        df.loc[mask_valor_nulo, 'ValidacaoValor'] = 'VALOR_NULO'
        df.loc[~mask_valor_nulo & (df['ValorDespesas'] <= 0), 'ValidacaoValor'] = 'VALOR_NAO_POSITIVO'
        
        df['ValidacaoRazao'] = 'RAZAO_VALIDA'
        razao_str = df['RazaoSocial'].astype(str)
        df.loc[df['RazaoSocial'].isna() | (razao_str.str.strip() == '') | (razao_str.str.lower() == 'nan'), 'ValidacaoRazao'] = 'RAZAO_VAZIA'
        
        # Performance: Valida cada identificador único apenas uma vez e mapeia de volta
        cnpj_unicos = df['CNPJ'].dropna().unique()
        mapa_validacao = {cnpj: self.validar_cnpj(cnpj)[1] for cnpj in cnpj_unicos}
        df['ValidacaoCNPJ'] = df['CNPJ'].map(mapa_validacao).fillna('CNPJ_VAZIO')
        
        return df

    def baixar_dados_cadastrais(self):
        # Download seguro com limite de tamanho (Anti-DoS) e urljoin
        logger.info("Buscando cadastro de operadoras da ANS...")
        
        for tentativa, url_base in enumerate([self.BASE_URL_CADASTRO_COMPLETO, self.BASE_URL_CADASTRO_ATIVAS], 1):
            try:
                response = requests.get(url_base, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                csv_links = [urljoin(url_base, a['href']) for a in soup.find_all('a', href=True) if a['href'].endswith('.csv')]
                
                if csv_links:
                    url_completa = csv_links[-1]

                    # Validação extra de segurança que garante que a URL pertence ao domínio da ANS
                    if not url_completa.startswith("https://dadosabertos.ans.gov.br"):
                        logger.warning(f"URL de download suspeita ignorada: {url_completa}")
                        continue

                    logger.info(f"Baixando: {url_completa.split('/')[-1]}")
                    
                    with requests.get(url_completa, stream=True, timeout=120) as r:
                        r.raise_for_status()
                        downloaded = 0
                        local_path = self.temp_dir / "operadoras_cadastro.csv"
                        with open(local_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if chunk:
                                    downloaded += len(chunk)
                                    if downloaded > self.MAX_DOWNLOAD_SIZE:
                                        raise ValueError(f"O arquivo excede o limite de {self.MAX_DOWNLOAD_SIZE / (1024*1024):.0f}MB.")
                                    f.write(chunk)
                    return local_path
            except Exception as e:
                logger.warning(f"Falha na tentativa {tentativa}: {e}")
                continue
        return None

    def ler_dados_cadastrais(self, arquivo_path):
        # Leitura resiliente com log detalhado de falhas de formato/codificação
        logger.info("Lendo dados cadastrais...")
        erros_tentativas = []
        for encoding in ['utf-8', 'iso-8859-1', 'cp1252']:
            for sep in [';', ',', '\t']:
                try:
                    df = pd.read_csv(arquivo_path, sep=sep, encoding=encoding, low_memory=False, dtype=str)
                    if len(df.columns) > 1:
                        return df
                except (pd.errors.ParserError, UnicodeDecodeError, FileNotFoundError, OSError) as e:
                    erros_tentativas.append(f"enc={encoding}, sep={repr(sep)} -> {e}")
                    continue
        
        detalhes = " | ".join(erros_tentativas)
        raise ValueError(f"Erro ao ler arquivo cadastral. Detalhes: {detalhes}")

    def enriquecer_dados(self, df_consolidado, df_cadastro):
        # Join inteligente priorizando Registro ANS para maximizar o match
        logger.info("Enriquecendo dados com informações cadastrais...")
        df_cadastro.columns = df_cadastro.columns.str.strip().str.upper()
        
        col_cnpj = next((c for c in df_cadastro.columns if 'CNPJ' in c), None)
        col_registro = next((c for c in df_cadastro.columns if c == 'REGISTRO_OPERADORA'), None)
        col_razao = next((c for c in df_cadastro.columns if c == 'RAZAO_SOCIAL'), None)
        col_uf = next((c for c in df_cadastro.columns if c in ['UF', 'SIGLA_UF']), None)
        
        # Identifica a chave primária disponível no cadastro (Preferência: Registro ANS)
        if not col_registro and not col_cnpj:
            logger.error("Nenhum identificador válido (CNPJ/Registro) encontrado no cadastro.")
            return df_consolidado

        chave_principal = col_registro if col_registro else col_cnpj
        campos_para_renomear = [
            (chave_principal, 'ChaveJoin'),
            (col_razao, 'RazaoSocialCadastro'),
            (col_uf, 'UF'),
        ]
        renomear = {col: novo_nome for col, novo_nome in campos_para_renomear if col}
        
        df_cad_slim = df_cadastro[list(renomear.keys())].rename(columns=renomear).copy()
        df_cad_slim['ChaveJoin'] = df_cad_slim['ChaveJoin'].astype(str).str.replace(r'\D', '', regex=True)
        df_cad_slim = df_cad_slim.drop_duplicates('ChaveJoin')
        
        df_final = df_consolidado.copy()
        df_final['ChaveJoin'] = df_final['CNPJ']
        
        df_merged = df_final.merge(df_cad_slim, on='ChaveJoin', how='left', indicator=True)
        
        if 'RazaoSocialCadastro' in df_merged.columns:
            mask = (df_merged['RazaoSocial'].isin(['N/A', '']) | df_merged['RazaoSocial'].isna()) & df_merged['RazaoSocialCadastro'].notna()
            df_merged.loc[mask, 'RazaoSocial'] = df_merged.loc[mask, 'RazaoSocialCadastro']
            df_merged = df_merged.drop(columns=['RazaoSocialCadastro'])

        df_merged['StatusEnriquecimento'] = np.where(df_merged['_merge'] == 'both', 'ENRIQUECIDO', 'SEM_CADASTRO')
        
        # Fallback de UF caso a coluna não tenha sido encontrada ou o match tenha falhado
        if 'UF' in df_merged.columns:
            df_merged['UF'] = df_merged['UF'].fillna('XX')
        else:
            df_merged['UF'] = 'XX'
            
        return df_merged.drop(columns=['ChaveJoin', '_merge'])

    def agregar_dados(self, df):
        # Agregação final com máscara combinada para otimização de memória
        logger.info("Agregando dados por Razão Social e UF...")
        
        mask_validos = (
            df['ValidacaoCNPJ'].isin(['CNPJ_VALIDO', 'REGISTRO_ANS_VALIDO']) & 
            (df['ValidacaoValor'] == 'VALOR_VALIDO') &
            ~df['RazaoSocial'].isin(['N/A', '', 'nan']) & 
            df['RazaoSocial'].notna()
        )
        df_v = df[mask_validos].copy()
        
        if df_v.empty:
            logger.warning(
                "Nenhum registro válido encontrado para agregação; "
                "retornando DataFrame vazio."
            )
            return pd.DataFrame()
                
        # Named aggregation para clareza e prevenção de falhas de índice
        agregado = df_v.groupby(['RazaoSocial', 'UF'], observed=True).agg(
            TotalDespesas=('ValorDespesas', 'sum'),
            MediaDespesas=('ValorDespesas', 'mean'),
            DesvioPadrao=('ValorDespesas', 'std'),
            QtdRegistros=('ValorDespesas', 'count')
        ).reset_index().fillna(0)
        
        return agregado.sort_values('TotalDespesas', ascending=False)

    def executar(self):
        # Orquestração do pipeline com tratamento de erro global e limpeza de ambiente
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
            
            # Limpeza resiliente de arquivos temporários
            for f in self.temp_dir.glob('*'):
                try:
                    f.unlink()
                except Exception as e:
                    logger.warning(f"Não foi possível remover temporário {f}: {e}")
            
            logger.info("\n✓ TESTE 2 CONCLUÍDO COM SUCESSO!")
        except Exception as e:
            logger.exception(f"Erro fatal no pipeline: {e}")
            raise

    def gerar_relatorio(self, df_validado, df_enriquecido, df_agregado):
        # Gera relatório técnico consolidando as métricas de integridade
        with open(self.output_dir / "relatorio_teste2.txt", 'w', encoding='utf-8') as f:
            f.write(f"RELATÓRIO TESTE 2\nTotal Registros Processados: {len(df_validado)}\n\n")
            f.write(f"VALIDAÇÃO CNPJ/ANS:\n{df_validado['ValidacaoCNPJ'].value_counts().to_string()}\n\n")
            f.write(f"STATUS ENRIQUECIMENTO:\n{df_enriquecido['StatusEnriquecimento'].value_counts().to_string()}\n\n")
            f.write(f"AGREGAÇÃO FINAL:\nTotal Grupos (Operadora/UF): {len(df_agregado)}\n")
            if not df_agregado.empty: 
                f.write(f"\nTop 10 Operadoras por Despesa:\n{df_agregado.head(10).to_string(index=False)}")

    def compactar_resultado(self):
        # Nome do arquivo conforme requisito: Teste_Mauricio_Alves.zip
        zip_path = self.output_dir / "Teste_Mauricio_Alves.zip"
        files_added = 0
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in self.output_dir.glob('*.*'):
                # Evita incluir o próprio zip se ele já existisse
                if f.suffix in ['.csv', '.txt'] and f.name != zip_path.name:
                    zipf.write(f, f.name)
                    files_added += 1
        
        if files_added == 0:
            logger.warning("Nenhum arquivo gerado para compactação.")

if __name__ == "__main__":
    caminhos = [
        '/app/input/consolidado_despesas.csv', 
        '../Teste1_ANS_Integration/output/consolidado_despesas.csv', 
        'output/consolidado_despesas.csv'
    ]
    # Localiza dinamicamente a fonte de dados (Docker vs Local)
    csv_path = next((p for p in caminhos if os.path.exists(p)), None)
    
    if csv_path:
        DataTransformation(csv_path).executar()
    else:
        logger.error(f"Fonte de dados não localizada. Caminhos verificados: {caminhos}")

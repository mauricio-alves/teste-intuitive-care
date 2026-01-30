import os
import zipfile
import logging
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Configuração de logging para monitorização detalhada do pipeline
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _get_env_int(env_name: str, default_value: int) -> int:
    # Obtém um valor inteiro de variável de ambiente com fallback seguro
    env_val = os.getenv(env_name)
    if env_val is None:
        return default_value
    try:
        val = int(env_val)
        return val if val > 0 else default_value
    except ValueError:
        logger.warning(f"Valor inválido para {env_name} ({env_val}). Usando padrão {default_value}.")
        return default_value

class DataTransformation:
    # Pipeline profissional para transformação, validação e enriquecimento de dados da ANS.

    # Configurações de Download e Segurança
    MAX_DOWNLOAD_SIZE = 150 * 1024 * 1024 # Limite de 150MB (Proteção Anti-DoS)
    ALLOWED_DOMAIN = "dadosabertos.ans.gov.br"

    # Constantes para validação de CNPJ (Evita recreação de listas em memória)
    FIRST_DIGIT_MULTIPLIERS = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    SECOND_DIGIT_MULTIPLIERS = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    
    # URLs oficiais para busca do cadastro de operadoras
    BASE_URL_CADASTRO_COMPLETO = "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude/"
    BASE_URL_CADASTRO_ATIVAS = "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/"

    # Configurações de Rede (Configuráveis via Docker/Ambiente)
    TIMEOUT_BUSCA = _get_env_int("TIMEOUT_BUSCA_SEG", 60)   # Aumentado para 60s padrão
    TIMEOUT_DOWNLOAD = _get_env_int("TIMEOUT_DOWNLOAD_SEG", 300) # Aumentado para 300s padrão
    
    def __init__(self, csv_consolidado_path):
        self.csv_consolidado = Path(csv_consolidado_path)
        self.output_dir = Path("output")
        self.temp_dir = Path("temp")
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        if not self.csv_consolidado.exists():
            raise FileNotFoundError(f"Ficheiro de entrada não encontrado: {csv_consolidado_path}")

    def _obter_digito_verificador_cnpj(self, base, multiplicadores):
        # Método auxiliar para o cálculo dos dígitos verificadores
        soma = sum(int(base[i]) * multiplicadores[i] for i in range(len(base)))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    def calcular_digito_verificador_cnpj(self, cnpj_base):
        # Implementa o algoritmo oficial de dígitos verificadores do CNPJ

        if cnpj_base is None:
            return None
        if not isinstance(cnpj_base, (str, int, np.integer)):
            return None
    
        cnpj_str = str(cnpj_base)
        if len(cnpj_str) != 12 or not cnpj_str.isdigit():
            return None
        
        d1 = self._obter_digito_verificador_cnpj(cnpj_str, self.FIRST_DIGIT_MULTIPLIERS)
        d2 = self._obter_digito_verificador_cnpj(cnpj_str + str(d1), self.SECOND_DIGIT_MULTIPLIERS)
        
        return str(d1) + str(d2)

    def validar_cnpj(self, cnpj):
        # Validação híbrida: Registro ANS (6 dígitos) ou CNPJ (14 dígitos)
        if pd.isna(cnpj) or str(cnpj).strip() == '':
            return False, 'CNPJ_VAZIO'
        
        cnpj_limpo = ''.join(c for c in str(cnpj) if c.isdigit())

        if len(cnpj_limpo) == 6:
            return True, 'REGISTRO_ANS_VALIDO'
        
        if len(cnpj_limpo) != 14:
            return False, 'CNPJ_TAMANHO_INVALIDO'
        
        if len(set(cnpj_limpo)) == 1:
            return False, 'CNPJ_DIGITOS_REPETIDOS'
        
        base = cnpj_limpo[:12]
        digitos_informados = cnpj_limpo[12:14]
        digitos_calculados = self.calcular_digito_verificador_cnpj(base)
        
        return (True, 'CNPJ_VALIDO') if digitos_calculados == digitos_informados else (False, 'CNPJ_DV_INVALIDO')

    def validar_dados(self, df):
        logger.info("A aplicar validações de dados e otimização de memória...")
        df = df.copy()
        
        # Verificação rigorosa de colunas obrigatórias
        cols_req = ['CNPJ', 'RazaoSocial', 'ValorDespesas']
        colunas_ausentes = [c for c in cols_req if c not in df.columns]
        if colunas_ausentes:
            raise KeyError(f"Colunas obrigatórias ausentes: {colunas_ausentes}. Esperadas: {cols_req}")
        
        # Conversão explícita de tipos
        df['ValorDespesas'] = pd.to_numeric(df['ValorDespesas'], errors='coerce')
        for col in ['Trimestre', 'Ano']:
            if col in df.columns: df[col] = df[col].astype('category')
        
        # Validação de valores financeiros
        df['ValidacaoValor'] = 'VALOR_VALIDO'
        mask_nulo = pd.isna(df['ValorDespesas'])
        df.loc[mask_nulo, 'ValidacaoValor'] = 'VALOR_NULO'
        df.loc[~mask_nulo & (df['ValorDespesas'] <= 0), 'ValidacaoValor'] = 'VALOR_NAO_POSITIVO'
        
        # Validação de Razão Social
        df['ValidacaoRazao'] = 'RAZAO_VALIDA'
        razao_str = df['RazaoSocial'].astype(str)
        df.loc[df['RazaoSocial'].isna() | (razao_str.str.strip() == '') | (razao_str.str.lower() == 'nan'), 'ValidacaoRazao'] = 'RAZAO_VAZIA'
        
        # Performance: Valida identificadores únicos uma única vez
        cnpj_unicos = df['CNPJ'].dropna().unique()
        mapa_validacao = {cnpj: self.validar_cnpj(cnpj)[1] for cnpj in cnpj_unicos}
        df['ValidacaoCNPJ'] = df['CNPJ'].map(mapa_validacao).fillna('CNPJ_VAZIO')
        
        return df

    def baixar_dados_cadastrais(self):
        logger.info("A procurar cadastro de operadoras da ANS...")
        
        for tentativa, url_base in enumerate([self.BASE_URL_CADASTRO_COMPLETO, self.BASE_URL_CADASTRO_ATIVAS], 1):
            try:
                response = requests.get(url_base, timeout=self.TIMEOUT_BUSCA)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                csv_links = [urljoin(url_base, a['href']) for a in soup.find_all('a', href=True) if a['href'].endswith('.csv')]
                
                if csv_links:
                    url_completa = csv_links[-1]
                    
                    # Validação estrita do domínio (netloc)
                    if urlparse(url_completa).netloc != self.ALLOWED_DOMAIN:
                        logger.warning(f"URL de download bloqueada (domínio não autorizado): {url_completa}")
                        continue

                    logger.info(f"A descarregar: {url_completa.split('/')[-1]}")
                    
                    with requests.get(url_completa, stream=True, timeout=self.TIMEOUT_DOWNLOAD) as r:
                        r.raise_for_status()
                        downloaded = 0
                        local_path = self.temp_dir / "operadoras_cadastro.csv"
                        with open(local_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if chunk:
                                    downloaded += len(chunk)
                                    if downloaded > self.MAX_DOWNLOAD_SIZE:
                                        raise ValueError(f"Ficheiro excede o limite de segurança ({self.MAX_DOWNLOAD_SIZE} bytes).")
                                    f.write(chunk)
                    return local_path
            except Exception as e:
                logger.warning(f"Falha na tentativa {tentativa}: {e}")
                continue
        return None

    def ler_dados_cadastrais(self, arquivo_path):
        # Leitura robusta do ficheiro CSV com tentativas de diferentes codificações e separadores
        logger.info("A ler dados cadastrais...")
        erros_tentativas = []
        for encoding in ['utf-8', 'iso-8859-1', 'cp1252']:
            for sep in [';', ',', '\t']:
                try:
                    df = pd.read_csv(arquivo_path, sep=sep, encoding=encoding, low_memory=False, dtype=str)
                    if len(df.columns) > 1: return df
                except (pd.errors.ParserError, UnicodeDecodeError, OSError) as e:
                    erros_tentativas.append(f"enc={encoding}, sep={repr(sep)} -> {e}")
        
        raise ValueError(f"Não foi possível ler o ficheiro cadastral. Tentativas: {' | '.join(erros_tentativas)}")

    def enriquecer_dados(self, df_consolidado, df_cadastro):
        # Enriquecimento de dados com informações cadastrais
        logger.info("A enriquecer dados com informações cadastrais...")
        df_cadastro.columns = df_cadastro.columns.str.strip().str.upper()
        
        # Remove coluna '_merge' se já existir para evitar conflitos no join
        if '_merge' in df_consolidado.columns: df_consolidado = df_consolidado.drop(columns=['_merge'])

        col_cnpj = next((c for c in df_cadastro.columns if 'CNPJ' in c), None)
        col_registro = next((c for c in df_cadastro.columns if c == 'REGISTRO_OPERADORA'), None)
        col_razao = next((c for c in df_cadastro.columns if c == 'RAZAO_SOCIAL'), None)
        col_uf = next((c for c in df_cadastro.columns if c in ['UF', 'SIGLA_UF']), None)
        
        if not col_registro and not col_cnpj:
            logger.error("Identificadores necessários não encontrados no cadastro.")
            return df_consolidado

        chave_src = col_registro if col_registro else col_cnpj
        campos = [(chave_src, 'ChaveJoin'), (col_razao, 'RazaoSocialCadastro'), (col_uf, 'UF')]
        renomear = {c: n for c, n in campos if c}
        
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
        df_merged['UF'] = df_merged['UF'].fillna('XX') if 'UF' in df_merged.columns else 'XX'
            
        return df_merged.drop(columns=['ChaveJoin', '_merge'])

    def agregar_dados(self, df):
        # Agregação de despesas por Razão Social e UF
        logger.info("A agregar dados por Razão Social e UF...")
        
        mask = (df['ValidacaoCNPJ'].isin(['CNPJ_VALIDO', 'REGISTRO_ANS_VALIDO']) & 
                (df['ValidacaoValor'] == 'VALOR_VALIDO') &
                ~df['RazaoSocial'].isin(['N/A', '', 'nan']) & df['RazaoSocial'].notna())
        df_v = df[mask].copy()
        
        if df_v.empty:
            logger.warning("Nenhum registro válido para agregação.")
            return pd.DataFrame()
        
        agregado = df_v.groupby(['RazaoSocial', 'UF'], observed=True).agg(
            TotalDespesas=('ValorDespesas', 'sum'),
            MediaDespesas=('ValorDespesas', 'mean'),
            DesvioPadrao=('ValorDespesas', 'std'),
            QtdRegistros=('ValorDespesas', 'count')
        ).reset_index()
        
        agregado[['TotalDespesas', 'MediaDespesas', 'QtdRegistros']] = agregado[['TotalDespesas', 'MediaDespesas', 'QtdRegistros']].fillna(0)
        
        return agregado.sort_values('TotalDespesas', ascending=False)

    def executar(self):
        # Execução do pipeline completo
        logger.info("="*60)
        logger.info("TESTE 2 - TRANSFORMAÇÃO E VALIDAÇÃO DE DADOS")
        logger.info("="*60)
        
        try:
            df = pd.read_csv(self.csv_consolidado, dtype={'CNPJ': str, 'RazaoSocial': str})
            
            df_v = self.validar_dados(df)
            df_v.to_csv(self.output_dir / "dados_validados.csv", index=False)
            
            cad_path = self.baixar_dados_cadastrais()
            df_e = self.enriquecer_dados(df_v, self.ler_dados_cadastrais(cad_path)) if cad_path else df_v
            df_e.to_csv(self.output_dir / "dados_enriquecidos.csv", index=False)
            
            df_a = self.agregar_dados(df_e)
            if not df_a.empty: df_a.to_csv(self.output_dir / "despesas_agregadas.csv", index=False)
            
            self.gerar_relatorio(df_v, df_e, df_a)
            self.compactar_resultado()
            
            # Limpeza do diretório temporário
            for f in self.temp_dir.glob('*'):
                try: f.unlink()
                except Exception as e: logger.warning(f"Erro ao limpar {f}: {e}")
            
            logger.info("\n✓ PIPELINE CONCLUÍDO COM SUCESSO!")
        except Exception as e:
            logger.exception(f"Erro fatal: {e}")
            raise

    def gerar_relatorio(self, df_v, df_e, df_a):
        # Geração de relatório resumido
        with open(self.output_dir / "relatorio_teste2.txt", 'w', encoding='utf-8') as f:
            f.write(f"RELATÓRIO TESTE 2\nTotal Registros: {len(df_v)}\n\n")
            f.write(f"VALIDAÇÃO CNPJ/ANS:\n{df_v['ValidacaoCNPJ'].value_counts().to_string()}\n\n")
            f.write(f"STATUS ENRIQUECIMENTO:\n{df_e['StatusEnriquecimento'].value_counts().to_string()}\n\n")
            f.write(f"AGREGAÇÃO: {len(df_a)} grupos gerados.\n")
            if not df_a.empty: f.write(f"\nTop 10:\n{df_a.head(10).to_string(index=False)}")

    def compactar_resultado(self):
        # Compactação dos ficheiros de saída
        zip_path = self.output_dir / "Teste_Mauricio_Alves.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in self.output_dir.glob('*.*'):
                if f.suffix in ['.csv', '.txt'] and f.name != zip_path.name:
                    zipf.write(f, f.name)

if __name__ == "__main__":
    caminhos = ['/app/input/consolidado_despesas.csv', '../Teste1_ANS_Integration/output/consolidado_despesas.csv', 'output/consolidado_despesas.csv']
    csv_path = next((p for p in caminhos if os.path.exists(p)), None)
    
    if csv_path:
        DataTransformation(csv_path).executar()
    else:
        logger.error(f"Ficheiro de entrada não localizado. Caminhos verificados: {caminhos}")

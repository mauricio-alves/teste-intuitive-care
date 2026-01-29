import zipfile
import logging
import requests
import pandas as pd
import numpy as np
from pathlib import Path
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataTransformation:
    # Pipeline de transformação e enriquecimento de dados
    BASE_URL_CADASTRO = "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/"
    
    def __init__(self, csv_consolidado_path):
        # Inicializa diretórios e caminhos
        self.csv_consolidado = Path(csv_consolidado_path)
        self.output_dir = Path("output")
        self.temp_dir = Path("temp")
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        if not self.csv_consolidado.exists():
            raise FileNotFoundError(f"Arquivo consolidado não encontrado: {csv_consolidado_path}")
    
    def calcular_digito_verificador_cnpj(self, cnpj_base):
        # Calcula os dígitos verificadores do CNPJ usando a lógica oficial da Receita Federal
        if len(cnpj_base) != 12:
            return None
            
        def obter_digito(base, multiplicadores):
            soma = sum(int(base[i]) * multiplicadores[i] for i in range(len(base)))
            resto = soma % 11
            return 0 if resto < 2 else 11 - resto
        
        # Pesos oficiais: primeiro DV usa 5 a 2 e 9 a 2; segundo DV usa 6 a 2 e 9 a 2
        multiplicadores_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        multiplicadores_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        
        d1 = obter_digito(cnpj_base, multiplicadores_1)
        d2 = obter_digito(cnpj_base + str(d1), multiplicadores_2)
        
        return str(d1) + str(d2)
    
    def validar_cnpj(self, cnpj):
        # Valida formato e dígitos verificadores do CNPJ
        if pd.isna(cnpj) or str(cnpj).strip() == '':
            return False, 'CNPJ_VAZIO'
        
        cnpj_limpo = ''.join(c for c in str(cnpj) if c.isdigit())

        # Aceitar Registro ANS (6 dígitos) ou CNPJ (14 dígitos)
        if len(cnpj_limpo) == 6:
            return True, 'REGISTRO_ANS_VALIDO'
        
        # Valida tamanho
        if len(cnpj_limpo) != 14:
            return False, 'CNPJ_TAMANHO_INVALIDO'
        
        # Valida se todos os dígitos são iguais (CNPJ inválido)
        if len(set(cnpj_limpo)) == 1:
            return False, 'CNPJ_DIGITOS_REPETIDOS'
        
        # Valida dígitos verificadores
        base = cnpj_limpo[:12]
        digitos_informados = cnpj_limpo[12:14]
        digitos_calculados = self.calcular_digito_verificador_cnpj(base)
        
        if digitos_calculados != digitos_informados:
            return False, 'CNPJ_DV_INVALIDO'
        
        return True, 'CNPJ_VALIDO'
    
    def validar_dados(self, df):
        # Aplica validações no DataFrame e otimiza uso de memória
        logger.info("Aplicando validações de dados e otimização de memória...")
        
        df = df.copy()
        
        # Otimização de Memória: converte colunas de baixa cardinalidade para categoria
        for col in ['Trimestre', 'Ano']:
            if col in df.columns:
                df[col] = df[col].astype('category')
        
        # Validação de valores numéricos positivos (vetorizada para performance)
        df['ValidacaoValor'] = 'VALOR_VALIDO'
        df.loc[df['ValorDespesas'] <= 0, 'ValidacaoValor'] = 'VALOR_NAO_POSITIVO'
        df.loc[pd.isna(df['ValorDespesas']), 'ValidacaoValor'] = 'VALOR_NULO'
        
        # Validação de Razão Social não vazia
        df['ValidacaoRazao'] = 'RAZAO_VALIDA'
        razao_str = df['RazaoSocial'].astype(str)
        df.loc[df['RazaoSocial'].isna() | (razao_str.str.strip() == '') | (razao_str.str.lower() == 'nan'), 'ValidacaoRazao'] = 'RAZAO_VAZIA'
        df.loc[df['RazaoSocial'].isin(['N/A']), 'ValidacaoRazao'] = 'RAZAO_NAO_DISPONIVEL'
        
        # Validação de CNPJ
        res_cnpj = df['CNPJ'].apply(self.validar_cnpj)
        df['ValidacaoCNPJ'] = [r[1] for r in res_cnpj]
        
        return df
        
    def baixar_dados_cadastrais(self):
        # Baixa o arquivo CSV mais recente de operadoras ativas
        logger.info(f"Baixando dados cadastrais de: {self.BASE_URL_CADASTRO}")
        
        try:
            response = requests.get(self.BASE_URL_CADASTRO, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Procura por arquivos CSV
            csv_files = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('.csv'):
                    csv_files.append(self.BASE_URL_CADASTRO + href)
            
            if not csv_files:
                raise Exception("Nenhum arquivo CSV encontrado no diretório")
            
            # Pega o arquivo mais recente (geralmente o último da lista)
            url_completa = csv_files[-1]
            
            logger.info(f"Baixando arquivo cadastral atualizado...")
            with requests.get(url_completa, stream=True, timeout=120) as r:
                r.raise_for_status()
                local_path = self.temp_dir / "operadoras_ativas.csv"
                with open(local_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk: f.write(chunk)
            
            logger.info(f"Arquivo salvo em: {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Erro ao baixar dados cadastrais: {e}")
            return None
    
    def ler_dados_cadastrais(self, arquivo_path):
        # Lê o arquivo CSV de dados cadastrais com resiliência
        logger.info("Lendo dados cadastrais...")
        
        for encoding in ['utf-8', 'iso-8859-1', 'cp1252']:
            for sep in [';', ',', '\t']:
                try:
                    df = pd.read_csv(arquivo_path, sep=sep, encoding=encoding, low_memory=False, dtype=str)
                    if len(df.columns) > 1:
                        logger.info(f"Arquivo lido com sucesso: {len(df)} registros")
                        return df
                except:
                    continue
        
        raise Exception("Não foi possível ler o arquivo de dados cadastrais")
    
    def enriquecer_dados(self, df_consolidado, df_cadastro):
        # Faz join entre dados consolidados e cadastrais
        logger.info("Enriquecendo dados com informações cadastrais...")
        
        # Normaliza colunas do cadastro
        df_cadastro.columns = df_cadastro.columns.str.strip().str.upper()
        
        # Identifica colunas necessárias dinamicamente
        mapa = {
            next((c for c in df_cadastro.columns if 'CNPJ' in c), 'CNPJ'): 'CNPJ',
            next((c for c in df_cadastro.columns if 'REGISTRO' in c), 'REG'): 'RegistroANS',
            next((c for c in df_cadastro.columns if 'MODALIDADE' in c), 'MOD'): 'Modalidade',
            next((c for c in df_cadastro.columns if c in ['UF', 'SIGLA_UF']), 'UF'): 'UF'
        }
        
        # Prepara DataFrame de cadastro para join e otimiza memória
        df_cadastro_slim = df_cadastro[list(mapa.keys())].rename(columns=mapa).copy()
        df_cadastro_slim['CNPJ'] = df_cadastro_slim['CNPJ'].astype(str).str.replace(r'\D', '', regex=True)
        
        # Remove duplicados mantendo o primeiro registro e otimiza tipos
        df_cadastro_slim = df_cadastro_slim.drop_duplicates(subset=['CNPJ'], keep='first')
        for col in ['Modalidade', 'UF']:
            df_cadastro_slim[col] = df_cadastro_slim[col].astype('category')
        
        # Faz o join
        df_enriquecido = df_consolidado.merge(
            df_cadastro_slim,
            on='CNPJ',
            how='left',
            indicator=True
        )
        
        # Marca registros sem match
        df_enriquecido['StatusEnriquecimento'] = np.where(df_enriquecido['_merge'] == 'both', 'ENRIQUECIDO', 'SEM_CADASTRO')
        df_enriquecido = df_enriquecido.drop('_merge', axis=1)
        
        # Permite novos valores em colunas categóricas antes do fillna
        if 'Modalidade' in df_enriquecido.columns:
            if df_enriquecido['Modalidade'].dtype.name == 'category':
                df_enriquecido['Modalidade'] = df_enriquecido['Modalidade'].cat.add_categories(['NAO_INFORMADO'])
            df_enriquecido['Modalidade'] = df_enriquecido['Modalidade'].fillna('NAO_INFORMADO')

        if 'UF' in df_enriquecido.columns:
            if df_enriquecido['UF'].dtype.name == 'category':
                df_enriquecido['UF'] = df_enriquecido['UF'].cat.add_categories(['XX'])
            df_enriquecido['UF'] = df_enriquecido['UF'].fillna('XX')
            
        # Para RegistroANS, como não é categórica, o fillna simples continua funcionando
        df_enriquecido['RegistroANS'] = df_enriquecido['RegistroANS'].fillna('NAO_ENCONTRADO')
        
        return df_enriquecido    
        
    def agregar_dados(self, df):
        # Agrega dados por RazaoSocial e UF (apenas registros válidos)
        logger.info("Agregando dados por operadora e UF...")
        
        # Filtra registros válidos (CNPJ ou Registro ANS)
        df_validos = df[
            (df['ValidacaoCNPJ'].isin(['CNPJ_VALIDO', 'REGISTRO_ANS_VALIDO'])) &
            (df['ValidacaoValor'] == 'VALOR_VALIDO') &
            df['ValorDespesas'].notna()
        ].copy()

        # Se não houver dados, retorna DataFrame vazio estruturado
        if df_validos.empty:
            logger.warning("Nenhum registro válido encontrado para agregação. Gerando arquivo vazio.")
            return pd.DataFrame(columns=['RazaoSocial', 'UF', 'TotalDespesas', 'MediaDespesas', 'DesvioPadrao', 'QtdRegistros'])
        
        # Agregação com observed=True para lidar com colunas categóricas vazias
        try:
            agregado = df_validos.groupby(['RazaoSocial', 'UF'], observed=True).agg({
                'ValorDespesas': [
                    ('TotalDespesas', 'sum'),
                    ('MediaDespesas', 'mean'),
                    ('DesvioPadrao', 'std'),
                    ('QtdRegistros', 'count')
                ]
            }).reset_index()
            
            # Simplifica nomes de colunas e ordena
            agregado.columns = ['RazaoSocial', 'UF', 'TotalDespesas', 'MediaDespesas', 'DesvioPadrao', 'QtdRegistros']
            agregado['DesvioPadrao'] = agregado['DesvioPadrao'].fillna(0)
            agregado = agregado.sort_values('TotalDespesas', ascending=False)
            
            return agregado
        except Exception as e:
            # Em caso de erro inesperado, retorna DataFrame vazio estruturado
            logger.error(f"Erro inesperado durante a agregação: {e}")
            return pd.DataFrame(columns=['RazaoSocial', 'UF', 'TotalDespesas', 'MediaDespesas', 'DesvioPadrao', 'QtdRegistros'])
        
    def executar(self):
        # Pipeline completo de transformação
        logger.info("="*60)
        logger.info("TESTE 2 - TRANSFORMAÇÃO E VALIDAÇÃO DE DADOS")
        logger.info("="*60)
        
        # Carrega dados consolidados do Teste 1
        df = pd.read_csv(self.csv_consolidado, dtype={'CNPJ': str})
        
        # Validação de dados
        df_validado = self.validar_dados(df)
        validado_path = self.output_dir / "dados_validados.csv"
        df_validado.to_csv(validado_path, index=False, encoding='utf-8')
        
        # Enriquecimento de dados
        cadastro_path = self.baixar_dados_cadastrais()
        if cadastro_path:
            df_cadastro = self.ler_dados_cadastrais(cadastro_path)
            df_enriquecido = self.enriquecer_dados(df_validado, df_cadastro)
            enriquecido_path = self.output_dir / "dados_enriquecidos.csv"
            df_enriquecido.to_csv(enriquecido_path, index=False, encoding='utf-8')
        else:
            df_enriquecido = df_validado
        
        # Agregação de dados
        df_agregado = self.agregar_dados(df_enriquecido)
        agregado_path = self.output_dir / "despesas_agregadas.csv"
        df_agregado.to_csv(agregado_path, index=False, encoding='utf-8')
        
        self.gerar_relatorio(df_validado, df_enriquecido, df_agregado)
        self.compactar_resultado()
        logger.info("\n✓ TESTE 2 CONCLUÍDO COM SUCESSO!")
    
    def gerar_relatorio(self, df_validado, df_enriquecido, df_agregado):
        # Gera relatório resumido das operações realizadas
        report_path = self.output_dir / "relatorio_teste2.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\nRELATÓRIO - TESTE 2: TRANSFORMAÇÃO E VALIDAÇÃO\n" + "="*60 + "\n\n")
            f.write(f"Total de registros: {len(df_validado)}\n\n")
            f.write("1. VALIDAÇÃO CNPJ:\n" + df_validado['ValidacaoCNPJ'].value_counts().to_string() + "\n")
            f.write("\n2. VALIDAÇÃO VALOR:\n" + df_validado['ValidacaoValor'].value_counts().to_string() + "\n")
            f.write("\n3. AGREGAÇÃO:\nTotal de grupos: " + str(len(df_agregado)) + "\n")
            f.write("Top 10 Operadoras:\n" + df_agregado.head(10).to_string(index=False) + "\n")

    def compactar_resultado(self):
        # Compacta arquivos de saída em um ZIP
        zip_path = self.output_dir / "Teste2_Transformacao.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for arquivo in self.output_dir.glob('*.*'):
                if arquivo.suffix in ['.csv', '.txt']:
                    zipf.write(arquivo, arquivo.name)


if __name__ == "__main__":
    # Define o caminho do arquivo CSV consolidado
    import os
    if os.path.exists('/app/input/consolidado_despesas.csv'):
        csv_path = '/app/input/consolidado_despesas.csv'
    elif os.path.exists('../Teste1_ANS_Integration/output/consolidado_despesas.csv'):
        csv_path = '../Teste1_ANS_Integration/output/consolidado_despesas.csv'
    else:
        csv_path = 'output/consolidado_despesas.csv' 
    
    pipeline = DataTransformation(csv_path)
    pipeline.executar()
    
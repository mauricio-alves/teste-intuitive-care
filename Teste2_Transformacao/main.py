import os
from urllib.parse import urljoin
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

    # URL principal: Cadastro completo de operadoras (com Registro ANS e CNPJ)
    BASE_URL_CADASTRO_COMPLETO = "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude/"
    
    # URL alternativa 1: Operadoras ativas (mais comum, usa CNPJ)
    BASE_URL_CADASTRO_ATIVAS = "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/"
    
    # URL alternativa 2: Registro ANS ativo
    BASE_URL_REGISTRO_ANS = "https://dadosabertos.ans.gov.br/FTP/Base_de_dados/Microdados/dados_dbc/operadoras/oper_com_registro_ativo/"
    
    def __init__(self, csv_consolidado_path):
        self.csv_consolidado = Path(csv_consolidado_path)
        self.output_dir = Path("output")
        self.temp_dir = Path("temp")
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        
        if not self.csv_consolidado.exists():
            raise FileNotFoundError(f"Arquivo consolidado não encontrado: {csv_consolidado_path}")
    
    def calcular_digito_verificador_cnpj(self, cnpj_base):
        # Calcula os dígitos verificadores do CNPJ usando algoritmo da Receita Federal
        if len(cnpj_base) != 12 or not str(cnpj_base).isdigit():
            return None
            
        def obter_digito(base, multiplicadores):
            soma = sum(int(base[i]) * multiplicadores[i] for i in range(len(base)))
            resto = soma % 11
            return 0 if resto < 2 else 11 - resto
        
        # Multiplicadores oficiais
        multiplicadores_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        multiplicadores_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        
        d1 = obter_digito(cnpj_base, multiplicadores_1)
        d2 = obter_digito(cnpj_base + str(d1), multiplicadores_2)
        
        return str(d1) + str(d2)
    
    def validar_cnpj(self, cnpj):
        # Valida formato e dígitos verificadores do CNPJ, aceita também Registro ANS
        if pd.isna(cnpj) or str(cnpj).strip() == '':
            return False, 'CNPJ_VAZIO'
        
        cnpj_limpo = ''.join(c for c in str(cnpj) if c.isdigit())

        # Aceita Registro ANS (6 dígitos) - comum nos dados da ANS
        if len(cnpj_limpo) == 6:
            return True, 'REGISTRO_ANS_VALIDO'
        
        # Valida tamanho CNPJ
        if len(cnpj_limpo) != 14:
            return False, 'CNPJ_TAMANHO_INVALIDO'
        
        # Valida dígitos todos iguais
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
        # Aplica validações no DataFrame com otimização de memória
        logger.info("Aplicando validações de dados...")
        
        df = df.copy()

        # Verifica colunas obrigatórias
        cols_obrigatorias = ['CNPJ', 'RazaoSocial', 'ValorDespesas']
        if not all(c in df.columns for c in cols_obrigatorias):
            raise KeyError(f"Colunas obrigatórias ausentes: {cols_obrigatorias}")
        
        # Otimização: colunas de baixa cardinalidade como categoria
        for col in ['Trimestre', 'Ano']:
            if col in df.columns:
                df[col] = df[col].astype('category')
        
        # Validação de valores (vetorizada)
        df['ValidacaoValor'] = 'VALOR_VALIDO'
        df.loc[df['ValorDespesas'] <= 0, 'ValidacaoValor'] = 'VALOR_NAO_POSITIVO'
        df.loc[pd.isna(df['ValorDespesas']), 'ValidacaoValor'] = 'VALOR_NULO'
        
        # Validação de Razão Social
        df['ValidacaoRazao'] = 'RAZAO_VALIDA'
        razao_str = df['RazaoSocial'].astype(str)
        df.loc[df['RazaoSocial'].isna() | (razao_str.str.strip() == '') | (razao_str.str.lower() == 'nan'), 'ValidacaoRazao'] = 'RAZAO_VAZIA'
        df.loc[df['RazaoSocial'].isin(['N/A']), 'ValidacaoRazao'] = 'RAZAO_NAO_DISPONIVEL'
        
        # Validação de CNPJ/Registro ANS
        res_cnpj = df['CNPJ'].apply(self.validar_cnpj)
        df['ValidacaoCNPJ'] = [r[1] for r in res_cnpj]
        
        return df
        
    def baixar_dados_cadastrais(self):
        # Baixa cadastro de operadoras - tenta múltiplas fontes
        logger.info("Buscando cadastro de operadoras da ANS...")
        
        # Tenta URL com cadastro completo primeiro (tem Registro ANS e CNPJ)
        for tentativa, url_base in enumerate([
            self.BASE_URL_CADASTRO_COMPLETO,
            self.BASE_URL_CADASTRO_ATIVAS
        ], 1):
            try:
                logger.info(f"Tentativa {tentativa}: {url_base}")
                response = requests.get(url_base, timeout=30)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Procura arquivos CSV (pega o mais recente)
                csv_files = []
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.endswith('.csv'):
                        csv_files.append(urljoin(url_base, href))
                
                if csv_files:
                    # Pega o arquivo mais recente (último na lista)
                    url_completa = csv_files[-1] 
                    logger.info(f"Baixando: {url_completa.split('/')[-1]}")
                    
                    with requests.get(url_completa, stream=True, timeout=120) as r:
                        r.raise_for_status()
                        local_path = self.temp_dir / "operadoras_cadastro.csv"
                        with open(local_path, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if chunk: f.write(chunk)
                    
                    logger.info(f"Cadastro salvo em: {local_path}")
                    return local_path
                    
            except Exception as e:
                logger.warning(f"Falha na tentativa {tentativa}: {e}")
                continue
        
        logger.error("Não foi possível baixar dados cadastrais")
        return None
    
    def ler_dados_cadastrais(self, arquivo_path):
        # Lê CSV de cadastro com resiliência a encodings
        logger.info("Lendo dados cadastrais...")
        
        for encoding in ['utf-8', 'iso-8859-1', 'cp1252']:
            for sep in [';', ',', '\t']:
                try:
                    df = pd.read_csv(arquivo_path, sep=sep, encoding=encoding, low_memory=False, dtype=str)
                    if len(df.columns) > 1:
                        logger.info(f"Cadastro lido: {len(df)} registros, {len(df.columns)} colunas")
                        logger.info(f"Colunas disponíveis: {', '.join(df.columns[:10].tolist())}...")
                        return df
                except Exception:
                    continue
        
        raise Exception("Não foi possível ler o arquivo cadastral")
    
    def enriquecer_dados(self, df_consolidado, df_cadastro):
        # Join inteligente: tenta por Registro ANS, depois por CNPJ
        logger.info("Enriquecendo dados com informações cadastrais...")
        
        df_cadastro.columns = df_cadastro.columns.str.strip().str.upper()
        
        # Identifica colunas dinamicamente
        col_cnpj = next((c for c in df_cadastro.columns if 'CNPJ' in c), None)
        col_registro = next((c for c in df_cadastro.columns if c == 'REGISTRO_OPERADORA'), None)
        col_razao = next((c for c in df_cadastro.columns if c == 'RAZAO_SOCIAL' or c == 'Razao_Social'), None)
        col_modalidade = next((c for c in df_cadastro.columns if 'MODALIDADE' in c), None)
        col_uf = next((c for c in df_cadastro.columns if c in ['UF', 'SIGLA_UF', 'SIGLA']), None)
        
        logger.info(f"Colunas identificadas - Registro: {col_registro}, CNPJ: {col_cnpj}, Razão: {col_razao}, UF: {col_uf}")
        
        # Prepara cadastro para join
        colunas_necessarias = []
        renomear = {}
        
        # Prioriza Registro ANS se disponível
        chave_join = None
        if col_registro:
            colunas_necessarias.append(col_registro)
            renomear[col_registro] = 'ChaveJoin'
            chave_join = 'REGISTRO_ANS'
        elif col_cnpj:
            colunas_necessarias.append(col_cnpj)
            renomear[col_cnpj] = 'ChaveJoin'
            chave_join = 'CNPJ'
        else:
            logger.error("Nenhuma chave válida encontrada no cadastro!")
            return df_consolidado
        
        # Adiciona outras colunas
        if col_razao:
            colunas_necessarias.append(col_razao)
            renomear[col_razao] = 'RazaoSocialCadastro'
        if col_modalidade:
            colunas_necessarias.append(col_modalidade)
            renomear[col_modalidade] = 'Modalidade'
        if col_uf:
            colunas_necessarias.append(col_uf)
            renomear[col_uf] = 'UF'
        
        df_cadastro_slim = df_cadastro[colunas_necessarias].rename(columns=renomear).copy()
        
        # Limpa chave de join (remove não-dígitos)
        df_cadastro_slim['ChaveJoin'] = df_cadastro_slim['ChaveJoin'].astype(str).str.replace(r'\D', '', regex=True)
        
        # Remove duplicados
        df_cadastro_slim = df_cadastro_slim.drop_duplicates(subset=['ChaveJoin'], keep='first')
        
        # Prepara chave no consolidado (CNPJ = Registro ANS nos nossos dados)
        df_consolidado_prep = df_consolidado.copy()
        df_consolidado_prep['ChaveJoin'] = df_consolidado_prep['CNPJ']
        
        # Join
        logger.info(f"Realizando join por {chave_join}...")
        df_enriquecido = df_consolidado_prep.merge(
            df_cadastro_slim,
            on='ChaveJoin',
            how='left',
            indicator=True
        )
        
        # Estatísticas do match
        total = len(df_enriquecido)
        com_match = (df_enriquecido['_merge'] == 'both').sum()
        sem_match = (df_enriquecido['_merge'] == 'left_only').sum()
        
        logger.info(f"Resultado do join:")
        logger.info(f"  Total: {total}")
        logger.info(f"  Com match: {com_match} ({com_match/total*100:.1f}%)")
        logger.info(f"  Sem match: {sem_match} ({sem_match/total*100:.1f}%)")
        
        # Atualiza RazaoSocial com dados do cadastro (se disponível)
        if 'RazaoSocialCadastro' in df_enriquecido.columns:
            # Sobrescreve N/A e vazios com dados do cadastro
            mascara_atualizar = (
                (df_enriquecido['RazaoSocial'].isin(['N/A', '']) | df_enriquecido['RazaoSocial'].isna()) &
                df_enriquecido['RazaoSocialCadastro'].notna()
            )
            df_enriquecido.loc[mascara_atualizar, 'RazaoSocial'] = df_enriquecido.loc[mascara_atualizar, 'RazaoSocialCadastro']
            df_enriquecido = df_enriquecido.drop('RazaoSocialCadastro', axis=1)
            
            razoes_atualizadas = mascara_atualizar.sum()
            logger.info(f"  Razões Sociais atualizadas: {razoes_atualizadas}")
        
        # Adiciona coluna RegistroANS se não existir
        if 'RegistroANS' not in df_enriquecido.columns:
            if chave_join == 'REGISTRO_ANS':
                df_enriquecido['RegistroANS'] = df_enriquecido['ChaveJoin']
            else:
                df_enriquecido['RegistroANS'] = 'NAO_ENCONTRADO'
        
        # Marca status de enriquecimento
        df_enriquecido['StatusEnriquecimento'] = np.where(
            df_enriquecido['_merge'] == 'both', 
            'ENRIQUECIDO', 
            'SEM_CADASTRO'
        )
        
        # Remove colunas auxiliares
        df_enriquecido = df_enriquecido.drop(['ChaveJoin', '_merge'], axis=1)
        
        # Preenche valores ausentes com padrões
        if 'Modalidade' in df_enriquecido.columns:
            df_enriquecido['Modalidade'] = df_enriquecido['Modalidade'].fillna('NAO_INFORMADO')
        if 'UF' in df_enriquecido.columns:
            df_enriquecido['UF'] = df_enriquecido['UF'].fillna('XX')
        if 'RegistroANS' in df_enriquecido.columns:
            df_enriquecido['RegistroANS'] = df_enriquecido['RegistroANS'].fillna('NAO_ENCONTRADO')
        
        return df_enriquecido
        
    def agregar_dados(self, df):
        # Agrega por RazaoSocial e UF
        logger.info("Agregando dados por Razão Social e UF...")
        
        # Filtra registros válidos
        df_validos = df[
            (df['ValidacaoCNPJ'].isin(['CNPJ_VALIDO', 'REGISTRO_ANS_VALIDO'])) &
            (df['ValidacaoValor'] == 'VALOR_VALIDO') &
            df['ValorDespesas'].notna()
        ].copy()
        
        # Remove registros sem Razão Social válida
        df_validos = df_validos[
            ~df_validos['RazaoSocial'].isin(['N/A', '', 'nan']) &
            df_validos['RazaoSocial'].notna()
        ]
        
        logger.info(f"Registros válidos para agregação: {len(df_validos)}")
        
        if df_validos.empty:
            logger.warning("Nenhum registro válido para agregação!")
            return pd.DataFrame(columns=[
                'RazaoSocial', 'UF', 'TotalDespesas', 
                'MediaDespesas', 'DesvioPadrao', 'QtdRegistros'
            ])
        
        # Verifica se UF existe
        if 'UF' not in df_validos.columns:
            logger.warning("Coluna UF não encontrada. Agregando apenas por RazaoSocial.")
            df_validos['UF'] = 'N/A'
        
        # Agregação com estatísticas
        try:
            agregado = df_validos.groupby(['RazaoSocial', 'UF'], observed=True).agg({
                'ValorDespesas': [
                    ('TotalDespesas', 'sum'),
                    ('MediaDespesas', 'mean'),
                    ('DesvioPadrao', 'std'),
                    ('QtdRegistros', 'count')
                ]
            }).reset_index()
            
            # Simplifica colunas
            agregado.columns = ['RazaoSocial', 'UF', 'TotalDespesas', 'MediaDespesas', 'DesvioPadrao', 'QtdRegistros']
            
            # Preenche desvio padrão NaN (quando há apenas 1 registro)
            agregado['DesvioPadrao'] = agregado['DesvioPadrao'].fillna(0)
            
            # Ordena por total (maior → menor)
            agregado = agregado.sort_values('TotalDespesas', ascending=False)
            
            logger.info(f"Agregação concluída: {len(agregado)} grupos gerados")
            logger.info(f"Top 3: {agregado.head(3)['RazaoSocial'].tolist()}")
            
            return agregado
            
        except Exception as e:
            logger.error(f"Erro na agregação: {e}")
            return pd.DataFrame(columns=[
                'RazaoSocial', 'UF', 'TotalDespesas', 
                'MediaDespesas', 'DesvioPadrao', 'QtdRegistros'
            ])
        
    def executar(self):
        # Pipeline completo
        logger.info("="*60)
        logger.info("TESTE 2 - TRANSFORMAÇÃO E VALIDAÇÃO DE DADOS")
        logger.info("="*60)
        
        # Carrega consolidado do Teste 1 e valida existência do arquivo CSV
        logger.info(f"Carregando: {self.csv_consolidado}")
        try:
            df = pd.read_csv(self.csv_consolidado, dtype={'CNPJ': str, 'RazaoSocial': str})
            logger.info(f"Registros carregados: {len(df)}")
        except FileNotFoundError as e:
            logger.error(f"Arquivo CSV não encontrado: {self.csv_consolidado} - Detalhes: {e}")
            return
        except pd.errors.ParserError as e:
            logger.error(f"Erro ao interpretar o arquivo CSV '{self.csv_consolidado}': {e}")
            return
        except UnicodeDecodeError as e:
            logger.error(f"Erro de codificação ao ler o arquivo CSV '{self.csv_consolidado}': {e}")
            return
        except Exception as e:
            logger.error(f"Erro inesperado ao ler o arquivo CSV '{self.csv_consolidado}': {e}")
            return
        
        # Validação
        df_validado = self.validar_dados(df)
        validado_path = self.output_dir / "dados_validados.csv"
        df_validado.to_csv(validado_path, index=False, encoding='utf-8')
        logger.info(f"✓ Validação concluída: {validado_path}")
        
        # Enriquecimento
        cadastro_path = self.baixar_dados_cadastrais()
        if cadastro_path:
            df_cadastro = self.ler_dados_cadastrais(cadastro_path)
            df_enriquecido = self.enriquecer_dados(df_validado, df_cadastro)
            
            enriquecido_path = self.output_dir / "dados_enriquecidos.csv"
            df_enriquecido.to_csv(enriquecido_path, index=False, encoding='utf-8')
            logger.info(f"✓ Enriquecimento concluído: {enriquecido_path}")
        else:
            logger.warning("Continuando sem enriquecimento...")
            df_enriquecido = df_validado
        
        # Agregação
        df_agregado = self.agregar_dados(df_enriquecido)
        agregado_path = self.output_dir / "despesas_agregadas.csv"
        df_agregado.to_csv(agregado_path, index=False, encoding='utf-8')
        logger.info(f"✓ Agregação concluída: {agregado_path}")
        
        # Relatório e compactação
        self.gerar_relatorio(df_validado, df_enriquecido, df_agregado)
        self.compactar_resultado()
        
        logger.info("\n✓ TESTE 2 CONCLUÍDO COM SUCESSO!")
    
    def gerar_relatorio(self, df_validado, df_enriquecido, df_agregado):
        # Gera relatório com estatísticas
        report_path = self.output_dir / "relatorio_teste2.txt"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("RELATÓRIO - TESTE 2: TRANSFORMAÇÃO E VALIDAÇÃO\n")
            f.write("="*60 + "\n\n")
            
            f.write(f"Total de registros: {len(df_validado)}\n\n")
            
            # Validações
            f.write("1. VALIDAÇÃO CNPJ:\n")
            f.write(df_validado['ValidacaoCNPJ'].value_counts().to_string() + "\n\n")
            
            f.write("2. VALIDAÇÃO VALOR:\n")
            f.write(df_validado['ValidacaoValor'].value_counts().to_string() + "\n\n")
            
            f.write("3. VALIDAÇÃO RAZÃO SOCIAL:\n")
            f.write(df_validado['ValidacaoRazao'].value_counts().to_string() + "\n\n")
            
            # Enriquecimento
            if 'StatusEnriquecimento' in df_enriquecido.columns:
                f.write("4. ENRIQUECIMENTO:\n")
                f.write(df_enriquecido['StatusEnriquecimento'].value_counts().to_string() + "\n\n")
            
            # Agregação
            f.write(f"5. AGREGAÇÃO:\n")
            f.write(f"Total de grupos (Operadora/UF): {len(df_agregado)}\n")
            
            if not df_agregado.empty:
                f.write(f"Total geral de despesas: R$ {df_agregado['TotalDespesas'].sum():,.2f}\n")
                f.write(f"\nTop 10 Operadoras:\n")
                f.write(df_agregado.head(10).to_string(index=False) + "\n")
        
        logger.info(f"✓ Relatório gerado: {report_path}")
    
    def compactar_resultado(self):
        # Compacta arquivos de saída
        zip_path = self.output_dir / "Teste_Mauricio_Alves.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for arquivo in self.output_dir.glob('*.*'):
                if arquivo.suffix in ['.csv', '.txt']:
                    zipf.write(arquivo, arquivo.name)
        
        logger.info(f"✓ Arquivos compactados: {zip_path}")

if __name__ == "__main__":
    # Define caminho do CSV consolidado    
    if os.path.exists('/app/input/consolidado_despesas.csv'):
        csv_path = '/app/input/consolidado_despesas.csv'
    elif os.path.exists('../Teste1_ANS_Integration/output/consolidado_despesas.csv'):
        csv_path = '../Teste1_ANS_Integration/output/consolidado_despesas.csv'
    else:
        csv_path = 'output/consolidado_despesas.csv'
    
    pipeline = DataTransformation(csv_path)
    pipeline.executar()

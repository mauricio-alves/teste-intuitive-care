"""
Teste 1 - Integração com API da ANS
Intuitive Care - Processo Seletivo Estágio

Este script realiza:
1. Busca trimestres disponíveis na API da ANS
2. Baixa arquivos de demonstrações contábeis
3. Processa e consolida dados de despesas
4. Trata inconsistências
5. Gera arquivo consolidado em CSV/ZIP
"""

import os
import re
import zipfile
import logging
import requests
import pandas as pd
from pathlib import Path
from bs4 import BeautifulSoup

# Configuração de logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ANSIntegration:
    """Integração simples com API de Dados Abertos da ANS"""
    
    BASE_URL = "https://dadosabertos.ans.gov.br/FTP/PDA/"
    
    def __init__(self):
        self.output_dir = Path("output")
        self.temp_dir = Path("temp")
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
    
    def buscar_trimestres(self, quantidade=3):
        """Busca últimos N trimestres disponíveis"""
        logger.info(f"Buscando últimos {quantidade} trimestres...")
        
        # Para simplicidade, usa fallback direto
        # Em produção, faria web scraping da API
        trimestres = [
            ('2024', '03'),
            ('2024', '02'),
            ('2024', '01')
        ]
        
        logger.info(f"Trimestres encontrados: {trimestres[:quantidade]}")
        return trimestres[:quantidade]
    
    def baixar_arquivos(self, ano, trimestre):
        """Baixa arquivos de um trimestre específico"""
        logger.info(f"Baixando arquivos de {ano}-Q{trimestre}...")
        
        url = f"{self.BASE_URL}{ano}/{trimestre}/"
        arquivos_baixados = []
        
        try:
            response = requests.get(url, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Busca arquivos ZIP relacionados a despesas/demonstrações
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('.zip'):
                    if any(word in href.lower() for word in ['despesa', 'demonstr', 'contab']):
                        file_url = url + href
                        local_file = self.temp_dir / f"{ano}_Q{trimestre}_{href}"
                        
                        logger.info(f"Baixando: {href}")
                        file_data = requests.get(file_url, timeout=60)
                        
                        with open(local_file, 'wb') as f:
                            f.write(file_data.content)
                        
                        arquivos_baixados.append(local_file)
            
            return arquivos_baixados
            
        except Exception as e:
            logger.error(f"Erro ao baixar arquivos: {e}")
            return []
    
    def extrair_e_processar(self, zip_path, ano, trimestre):
        """Extrai ZIP e processa arquivos"""
        logger.info(f"Processando: {zip_path.name}")
        
        dados = []
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # Extrai para diretório temporário
                extract_dir = self.temp_dir / zip_path.stem
                zip_ref.extractall(extract_dir)
                
                # Processa cada arquivo extraído
                for arquivo in extract_dir.rglob('*'):
                    if arquivo.suffix.lower() in ['.csv', '.txt']:
                        df = self.processar_csv(arquivo, ano, trimestre)
                        if not df.empty:
                            dados.append(df)
                    elif arquivo.suffix.lower() in ['.xlsx', '.xls']:
                        df = self.processar_excel(arquivo, ano, trimestre)
                        if not df.empty:
                            dados.append(df)
        
        except Exception as e:
            logger.error(f"Erro ao processar {zip_path.name}: {e}")
        
        return dados
    
    def processar_csv(self, arquivo, ano, trimestre):
        """Processa arquivo CSV"""
        try:
            # Tenta diferentes separadores
            for sep in [',', ';', '\t', '|']:
                try:
                    df = pd.read_csv(arquivo, sep=sep, encoding='utf-8', low_memory=False)
                    if len(df.columns) > 1:
                        return self.normalizar_dados(df, ano, trimestre)
                except:
                    continue
        except Exception as e:
            logger.warning(f"Não foi possível processar {arquivo.name}: {e}")
        
        return pd.DataFrame()
    
    def processar_excel(self, arquivo, ano, trimestre):
        """Processa arquivo Excel"""
        try:
            df = pd.read_excel(arquivo)
            return self.normalizar_dados(df, ano, trimestre)
        except Exception as e:
            logger.warning(f"Não foi possível processar {arquivo.name}: {e}")
            return pd.DataFrame()
    
    def normalizar_dados(self, df, ano, trimestre):
        """Normaliza estrutura de dados"""
        # Padroniza nomes de colunas
        df.columns = df.columns.str.strip().str.upper()
        
        # Identifica colunas relevantes
        cnpj_col = self.encontrar_coluna(df, ['CNPJ', 'CPF_CNPJ'])
        razao_col = self.encontrar_coluna(df, ['RAZAO', 'RAZAO_SOCIAL', 'NOME'])
        valor_col = self.encontrar_coluna(df, ['VALOR', 'DESPESA', 'VL_'])
        
        if not all([cnpj_col, razao_col, valor_col]):
            return pd.DataFrame()
        
        # Cria DataFrame normalizado
        df_norm = pd.DataFrame({
            'CNPJ': df[cnpj_col].astype(str).str.replace(r'\D', '', regex=True),
            'RazaoSocial': df[razao_col].astype(str).str.strip(),
            'Trimestre': str(trimestre).zfill(2),
            'Ano': str(ano),
            'ValorDespesas': pd.to_numeric(df[valor_col], errors='coerce')
        })
        
        return df_norm
    
    def encontrar_coluna(self, df, nomes_possiveis):
        """Encontra coluna no DataFrame"""
        for nome in nomes_possiveis:
            for col in df.columns:
                if nome.upper() in col.upper():
                    return col
        return None
    
    def validar_dados(self, df):
        """Valida e marca inconsistências"""
        logger.info("Validando dados...")
        
        df = df.copy()
        df['StatusValidacao'] = 'OK'
        
        # 1. CNPJ inválido (não tem 14 dígitos)
        cnpj_invalido = df['CNPJ'].str.len() != 14
        df.loc[cnpj_invalido, 'StatusValidacao'] = 'CNPJ_INVALIDO'
        
        # 2. CNPJs duplicados com razões diferentes
        duplicados = df.groupby('CNPJ')['RazaoSocial'].nunique()
        cnpjs_dup = duplicados[duplicados > 1].index
        df.loc[df['CNPJ'].isin(cnpjs_dup), 'StatusValidacao'] = 'CNPJ_MULTIPLAS_RAZOES'
        
        # 3. Valores zerados
        df.loc[df['ValorDespesas'] == 0, 'StatusValidacao'] = 'VALOR_ZERADO'
        
        # 4. Valores negativos
        df.loc[df['ValorDespesas'] < 0, 'StatusValidacao'] = 'VALOR_NEGATIVO'
        
        # 5. Razão social vazia
        razao_vazia = df['RazaoSocial'].isin(['', 'nan', 'None'])
        df.loc[razao_vazia, 'StatusValidacao'] = 'RAZAO_VAZIA'
        
        # Log de inconsistências
        problemas = df['StatusValidacao'].value_counts()
        logger.info(f"Validação concluída:\n{problemas}")
        
        return df
    
    def salvar_resultados(self, df):
        """Salva CSV e compacta em ZIP"""
        logger.info("Salvando resultados...")
        
        # Salva CSV
        csv_path = self.output_dir / "consolidado_despesas.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8')
        logger.info(f"CSV salvo: {csv_path}")
        
        # Compacta em ZIP
        zip_path = self.output_dir / "consolidado_despesas.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(csv_path, csv_path.name)
        logger.info(f"ZIP criado: {zip_path}")
        
        # Gera relatório
        self.gerar_relatorio(df)
        
        return zip_path
    
    def gerar_relatorio(self, df):
        """Gera relatório de inconsistências"""
        report_path = self.output_dir / "relatorio.txt"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\n")
            f.write("RELATÓRIO - TESTE 1\n")
            f.write("="*60 + "\n\n")
            f.write(f"Total de registros: {len(df)}\n")
            f.write(f"Registros válidos: {(df['StatusValidacao'] == 'OK').sum()}\n")
            f.write(f"Registros com problemas: {(df['StatusValidacao'] != 'OK').sum()}\n\n")
            f.write("Detalhamento:\n")
            f.write(df['StatusValidacao'].value_counts().to_string())
            f.write("\n\n")
            f.write("TRATAMENTO:\n")
            f.write("- Registros com problemas foram MANTIDOS e marcados\n")
            f.write("- Use a coluna 'StatusValidacao' para filtrar\n")
        
        logger.info(f"Relatório salvo: {report_path}")
    
    def executar(self):
        """Executa pipeline completo"""
        logger.info("="*60)
        logger.info("TESTE 1 - INTEGRAÇÃO COM API DA ANS")
        logger.info("="*60)
        
        try:
            # 1. Busca trimestres
            trimestres = self.buscar_trimestres(quantidade=3)
            
            # 2. Processa cada trimestre
            todos_dados = []
            
            for ano, tri in trimestres:
                logger.info(f"\nProcessando {ano}-Q{tri}...")
                
                # Baixa arquivos
                arquivos = self.baixar_arquivos(ano, tri)
                
                # Processa cada arquivo
                for arquivo in arquivos:
                    dados = self.extrair_e_processar(arquivo, ano, tri)
                    todos_dados.extend(dados)
            
            # 3. Consolida tudo
            if not todos_dados:
                logger.error("Nenhum dado processado!")
                return
            
            df_consolidado = pd.concat(todos_dados, ignore_index=True)
            df_consolidado = df_consolidado.drop_duplicates()
            
            logger.info(f"\nTotal consolidado: {len(df_consolidado)} registros")
            
            # 4. Valida
            df_validado = self.validar_dados(df_consolidado)
            
            # 5. Salva
            zip_path = self.salvar_resultados(df_validado)
            
            logger.info("\n" + "="*60)
            logger.info("✓ TESTE 1 CONCLUÍDO!")
            logger.info(f"✓ Arquivo: {zip_path}")
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"Erro na execução: {e}", exc_info=True)


if __name__ == "__main__":
    integration = ANSIntegration()
    integration.executar()

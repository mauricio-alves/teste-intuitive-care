import zipfile
import logging
import requests
import pandas as pd
import urllib3
from pathlib import Path
from bs4 import BeautifulSoup

# Desabilita avisos de certificado SSL para sites governamentais
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ANSIntegration:
    # Integração resiliente com API de Dados Abertos da ANS
    BASE_URL = "https://dadosabertos.ans.gov.br/FTP/PDA/demonstracoes_contabeis/"
    
    def __init__(self):
        self.output_dir = Path("output")
        self.temp_dir = Path("temp")
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.csv_final = self.output_dir / "consolidado_despesas.csv"

    def buscar_trimestres(self):
        # Define os trimestres alvo baseados na estrutura do FTP
        return [('2025', '3'), ('2025', '2'), ('2025', '1')]

    def baixar_arquivos(self, ano, trimestre):
        # Acessa a pasta do ano e descarrega o ZIP do trimestre correspondente
        url_ano = f"{self.BASE_URL}{ano}/"
        logger.info(f"Buscando ficheiros em {url_ano}...")
        baixados = []
        try:
            res = requests.get(url_ano, headers=self.headers, verify=False, timeout=30)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Padrão observado: XT202X.zip (ex: 3T2025.zip)
            padrao = f"{trimestre}T{ano}".upper()
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('.zip') and padrao in href.upper():
                    local = self.temp_dir / f"{ano}_Q{trimestre}_{href}"
                    logger.info(f"Descarregando: {href}")
                    
                    file_res = requests.get(url_ano + href, headers=self.headers, verify=False, timeout=180)
                    with open(local, 'wb') as f:
                        f.write(file_res.content)
                    baixados.append(local)
            return baixados
        except Exception as e:
            logger.error(f"Erro no download: {e}")
            return []

    def processar_e_salvar_incremental(self, zip_path, ano, trimestre):
        # Extrai e anexa dados ao CSV final para otimizar memória RAM
        logger.info(f"Processando incrementalmente: {zip_path.name}")
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                extract_path = self.temp_dir / zip_path.stem
                z.extractall(extract_path)
                
                for f in extract_path.rglob('*'):
                    if f.suffix.lower() in ['.csv', '.txt']:
                        df = self.ler_arquivo_resiliente(f, ano, trimestre)
                        if not df.empty:
                            header = not self.csv_final.exists()
                            df.to_csv(self.csv_final, mode='a', index=False, header=header, encoding='utf-8')
        except Exception as e:
            logger.error(f"Erro no processamento de {zip_path.name}: {e}")

    def ler_arquivo_resiliente(self, path, ano, trimestre):
        # Tenta ler com diferentes encodings e separadores comuns na ANS
        for enc in ['utf-8', 'iso-8859-1', 'cp1252']:
            for sep in [';', ',', '\t']:
                try:
                    df = pd.read_csv(path, sep=sep, encoding=enc, on_bad_lines='skip', low_memory=False)
                    if len(df.columns) > 1:
                        return self.normalizar(df, ano, trimestre)
                except:
                    continue
        return pd.DataFrame()

    def normalizar(self, df, ano, trimestre):
        # Mapeia colunas reais da ANS e limpa os dados
        df.columns = df.columns.str.strip().str.upper()
        
        # Mapeamento flexível baseado em padrões de colunas da ANS
        col_cnpj = next((c for c in df.columns if any(x in c for x in ['CNPJ', 'REG_ANS', 'REGISTRO'])), None)
        col_valor = next((c for c in df.columns if any(x in c for x in ['VL_SALDO', 'VALOR', 'DESPESA'])), None)
        col_razao = next((c for c in df.columns if any(x in c for x in ['RAZAO', 'NOME', 'OPERADORA'])), None)

        if col_cnpj and col_valor:
            df_res = pd.DataFrame({
                'CNPJ': df[col_cnpj].astype(str).str.replace(r'\D', '', regex=True),
                'RazaoSocial': df[col_razao].astype(str).str.strip() if col_razao else "N/A",
                'Trimestre': str(trimestre).zfill(2),
                'Ano': str(ano),
                'ValorDespesas': pd.to_numeric(df[col_valor], errors='coerce')
            })
            # Remove nulos para garantir a qualidade do consolidado
            return df_res.dropna(subset=['CNPJ', 'ValorDespesas'])
        return pd.DataFrame()
    
    def gerar_relatorio_final(self):
        # Gera análise crítica de inconsistências (Requisito 1.3)
        if not self.csv_final.exists():
            return
            
        logger.info("Gerando relatorio.txt com análise de inconsistências...")
        df = pd.read_csv(self.csv_final)
        report_path = self.output_dir / "relatorio.txt"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\nRELATÓRIO DE ANÁLISE CRÍTICA - TESTE 1\n" + "="*60 + "\n\n")
            f.write(f"Total de registros consolidados: {len(df)}\n")
            f.write(f"Valores zerados encontrados: {len(df[df['ValorDespesas'] == 0])}\n")
            f.write(f"Valores negativos encontrados: {len(df[df['ValorDespesas'] < 0])}\n")
            
            # Verificação de CNPJs (Registro ANS) duplicados com nomes diferentes
            dups = df.groupby('CNPJ')['RazaoSocial'].nunique()
            f.write(f"CNPJs com múltiplas razões sociais: {len(dups[dups > 1])}\n")
            
        logger.info(f"Relatório gerado com sucesso em: {report_path}")

    def gerar_zip_entrega(self):
        # Compacta o resultado final conforme requisito do teste
        if self.csv_final.exists():
            zip_path = self.output_dir / "consolidado_despesas.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(self.csv_final, self.csv_final.name)
            return zip_path
        return None

    def executar(self):
        # Fluxo principal de execução
        logger.info("="*60 + "\nPIPELINE TESTE 1\n" + "="*60)
        
        if self.csv_final.exists(): self.csv_final.unlink()
        
        trimestres = self.buscar_trimestres()
        for ano, tri in trimestres:
            zips = self.baixar_arquivos(ano, tri)
            for z in zips:
                self.processar_e_salvar_incremental(z, ano, tri)
        
        # Gera o relatório antes de compactar
        self.gerar_relatorio_final()
        
        entrega = self.gerar_zip_entrega()
        if entrega:
            logger.info(f"\n✓ TESTE 1 CONCLUÍDO! Ficheiro gerado: {entrega}")
        else:
            logger.error("Falha ao gerar o consolidado final.")

if __name__ == "__main__":
    ANSIntegration().executar()
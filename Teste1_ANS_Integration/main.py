import zipfile
import logging
import requests
import pandas as pd
import urllib3
import shutil
from pathlib import Path
from bs4 import BeautifulSoup

# Desabilita avisos apenas se necessário, mas mantendo o registro
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ANSIntegration:
    # Integração robusta com API de Dados Abatidos da ANS com foco em segurança e escalabilidade
    BASE_URL = "https://dadosabertos.ans.gov.br/FTP/PDA/demonstracoes_contabeis/"
    
    def __init__(self):
        self.output_dir = Path("output")
        self.temp_dir = Path("temp")
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.csv_final = self.output_dir / "consolidado_despesas.csv"

    def buscar_trimestres(self):
        return [('2024', '3'), ('2024', '2'), ('2024', '1')]

    def baixar_arquivos(self, ano, trimestre):
        url_ano = f"{self.BASE_URL}{ano}/"
        logger.info(f"Buscando arquivos em {url_ano}...")
        baixados = []
        
        try:
            # Validação de Status HTTP
            res = requests.get(url_ano, headers=self.headers, verify=False, timeout=30)
            res.raise_for_status() 
            
            soup = BeautifulSoup(res.text, 'html.parser')
            padrao = f"{trimestre}T{ano}".upper()
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('.zip') and padrao in href.upper():
                    local = self.temp_dir / f"{ano}_Q{trimestre}_{href}"
                    logger.info(f"Baixando: {href}")
                    
                    # Download via streaming para poupar RAM
                    with requests.get(url_ano + href, headers=self.headers, verify=False, timeout=180, stream=True) as r:
                        r.raise_for_status()
                        with open(local, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                f.write(chunk)
                    baixados.append(local)
            return baixados
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de rede ao buscar {url_ano}: {e}")
            return []

    def processar_e_salvar_incremental(self, zip_path, ano, trimestre):
        logger.info(f"Processando incrementalmente: {zip_path.name}")
        extract_path = self.temp_dir / zip_path.stem
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                # Proteção contra Zip Slip
                base_path = extract_path.resolve()
                for member in z.infolist():
                    member_path = (extract_path / member.filename).resolve()
                    if base_path not in member_path.parents and member_path != base_path:
                        logger.warning(f"Tentativa de Zip Slip detectada no arquivo {member.filename}. Ignorando.")
                        continue
                    z.extract(member, extract_path)
                
                for f in extract_path.rglob('*'):
                    if f.suffix.lower() in ['.csv', '.txt']:
                        df = self.ler_arquivo_resiliente(f, ano, trimestre)
                        if not df.empty:
                            header = not self.csv_final.exists()
                            df.to_csv(self.csv_final, mode='a', index=False, header=header, encoding='utf-8')
                            
        except Exception as e:
            logger.error(f"Erro no processamento de {zip_path.name}: {e}")
        finally:
            # Limpeza de ficheiros temporários após processar cada ZIP
            if extract_path.exists():
                shutil.rmtree(extract_path)
            if zip_path.exists():
                zip_path.unlink()

    def ler_arquivo_resiliente(self, path, ano, trimestre):
        # Captura de exceções específicas de parsing
        for enc in ['utf-8', 'iso-8859-1', 'cp1252']:
            for sep in [';', ',', '\t']:
                try:
                    df = pd.read_csv(path, sep=sep, encoding=enc, on_bad_lines='skip', low_memory=False)
                    if len(df.columns) > 1:
                        return self.normalizar(df, ano, trimestre)
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
                except Exception as e:
                    logger.debug(f"Erro inesperado ao ler {path.name}: {e}")
                    continue
        return pd.DataFrame()

    def normalizar(self, df, ano, trimestre):
        df.columns = df.columns.str.strip().str.upper()
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
            
            df_res = df_res.dropna(subset=['CNPJ', 'ValorDespesas'])
            df_res['StatusValidacao'] = 'OK'
            df_res.loc[df_res['CNPJ'].str.len() != 14, 'StatusValidacao'] = 'CNPJ_INVALIDO'
            df_res.loc[df_res['ValorDespesas'] == 0, 'StatusValidacao'] = 'VALOR_ZERADO'
            df_res.loc[df_res['ValorDespesas'] < 0, 'StatusValidacao'] = 'VALOR_NEGATIVO'
            df_res.loc[df_res['RazaoSocial'].isin(['N/A', '', 'nan']), 'StatusValidacao'] = 'RAZAO_VAZIA'
            
            return df_res
        return pd.DataFrame()
    
    def aplicar_validacao_duplicados_incremental(self):
        # Validação de duplicados via chunks (escalável para GBs de dados)
        if not self.csv_final.exists():
            return
            
        logger.info("Mapeando duplicados incrementalmente...")
        mapa_cnpj_raz = {}
        chunksize = 100000 
        
        # Mapear relações CNPJ -> Razão Social sem carregar tudo na RAM
        for chunk in pd.read_csv(self.csv_final, chunksize=chunksize, usecols=['CNPJ', 'RazaoSocial']):
            for cnpj, razao in zip(chunk['CNPJ'], chunk['RazaoSocial']):
                if pd.isna(cnpj): continue
                razao_str = str(razao)
                if cnpj not in mapa_cnpj_raz:
                    mapa_cnpj_raz[cnpj] = {razao_str}
                else:
                    mapa_cnpj_raz[cnpj].add(razao_str)
        
        cnpjs_dup = {cnpj for cnpj, razoes in mapa_cnpj_raz.items() if len(razoes) > 1}
        
        if cnpjs_dup:
            logger.info(f"Atualizando {len(cnpjs_dup)} CNPJs duplicados no ficheiro final...")
            temp_path = self.csv_final.with_suffix('.tmp')
            primeiro = True
            
            # Reescrever ficheiro final aplicando a marcação
            for chunk in pd.read_csv(self.csv_final, chunksize=chunksize):
                mask = chunk['CNPJ'].isin(cnpjs_dup)
                chunk.loc[mask, 'StatusValidacao'] = 'CNPJ_MULTIPLAS_RAZOES'
                chunk.to_csv(temp_path, mode='a', index=False, header=primeiro, encoding='utf-8')
                primeiro = False
            
            temp_path.replace(self.csv_final)
            logger.info("Validação de duplicados concluída.")
    
    def gerar_relatorio_final(self):
        if not self.csv_final.exists():
            return
            
        logger.info("Gerando relatorio.txt...")
        report_path = self.output_dir / "relatorio.txt"
        
        # Uso de chunks para contar estatísticas (evita ler arquivo inteiro)
        status_counts = {}
        total = 0
        for chunk in pd.read_csv(self.csv_final, chunksize=100000, usecols=['StatusValidacao']):
            total += len(chunk)
            counts = chunk['StatusValidacao'].value_counts().to_dict()
            for s, c in counts.items():
                status_counts[s] = status_counts.get(s, 0) + c

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\nRELATÓRIO DE ANÁLISE CRÍTICA - TESTE 1\n" + "="*60 + "\n\n")
            f.write(f"Total de registros consolidados: {total}\n\n")
            f.write("INCONSISTÊNCIAS ENCONTRADAS:\n" + "-"*60 + "\n")
            for status, count in status_counts.items():
                f.write(f"  {status}: {count}\n")
            f.write("\n" + "="*60 + "\nTRATAMENTO APLICADO:\n" + "-"*60 + "\n")
            f.write("Todos os registros com problemas foram MANTIDOS e MARCADOS na coluna 'StatusValidacao'.\n")

    def gerar_zip_entrega(self):
        if self.csv_final.exists():
            zip_path = self.output_dir / "consolidado_despesas.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(self.csv_final, self.csv_final.name)
            return zip_path
        return None

    def executar(self):
        logger.info("PIPELINE TESTE 1 - INTEGRAÇÃO ANS")
        if self.csv_final.exists(): self.csv_final.unlink()
        
        for ano, tri in self.buscar_trimestres():
            zips = self.baixar_arquivos(ano, tri)
            for z in zips:
                self.processar_e_salvar_incremental(z, ano, tri)
        
        self.aplicar_validacao_duplicados_incremental()
        self.gerar_relatorio_final()
        
        entrega = self.gerar_zip_entrega()
        if entrega: logger.info(f"✓ TESTE 1 CONCLUÍDO! Arquivo: {entrega}")

if __name__ == "__main__":
    ANSIntegration().executar()
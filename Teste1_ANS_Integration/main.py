import zipfile
import logging
import requests
import pandas as pd
import urllib3
import shutil
from pathlib import Path
from bs4 import BeautifulSoup

# Desabilita avisos de certificado SSL para sites governamentais (necessário para a API da ANS)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ANSIntegration:
    # Integração robusta com API da ANS focada em integridade de dados e segurança.
    BASE_URL = "https://dadosabertos.ans.gov.br/FTP/PDA/demonstracoes_contabeis/"
    
    def __init__(self):
        self.output_dir = Path("output")
        self.temp_dir = Path("temp")
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.csv_final = self.output_dir / "consolidado_despesas.csv"

    def buscar_trimestres(self):
        # Define os trimestres alvo para processamento
        return [('2024', '3'), ('2024', '2'), ('2024', '1')]

    def baixar_arquivos(self, ano, trimestre):
        url_ano = f"{self.BASE_URL}{ano}/"
        logger.info(f"Buscando arquivos em {url_ano}...")
        baixados = []
        
        try:
            # Validação de Status HTTP antes de parsear HTML
            res = requests.get(url_ano, headers=self.headers, verify=False, timeout=30)
            res.raise_for_status() 
            
            soup = BeautifulSoup(res.text, 'html.parser')
            padrao = f"{trimestre}T{ano}".upper()
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('.zip') and padrao in href.upper():
                    local = self.temp_dir / f"{ano}_Q{trimestre}_{href}"
                    logger.info(f"Baixando: {href}")
                    
                    # Download via Streaming com verificação de chunks (Sugestão Copilot)
                    with requests.get(url_ano + href, headers=self.headers, verify=False, timeout=180, stream=True) as r:
                        r.raise_for_status()
                        with open(local, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                # Evita chunks vazios de keep-alive
                                if chunk: 
                                    f.write(chunk)
                    baixados.append(local)
            return baixados
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de rede ao acessar a API: {e}")
            return []

    def processar_e_salvar_incremental(self, zip_path, ano, trimestre):
        logger.info(f"Processando incrementalmente: {zip_path.name}")
        extract_path = self.temp_dir / zip_path.stem
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                # Proteção contra ataque Zip Slip
                base_path = extract_path.resolve()
                for member in z.infolist():
                    member_path = (extract_path / member.filename).resolve()
                    if base_path not in member_path.parents and member_path != base_path:
                        logger.warning(f"Caminho inseguro detectado no ZIP: {member.filename}. Ignorando.")
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
            # Limpeza rigorosa de temporários
            if extract_path.exists():
                shutil.rmtree(extract_path)
            if zip_path.exists():
                zip_path.unlink()

    def ler_arquivo_resiliente(self, path, ano, trimestre):
        # Tipagem explícita para evitar que CNPJs percam zeros à esquerda
        for enc in ['utf-8', 'iso-8859-1', 'cp1252']:
            for sep in [';', ',', '\t']:
                try:
                    df = pd.read_csv(path, sep=sep, encoding=enc, on_bad_lines='skip', 
                                    # Lê tudo como string inicialmente 
                                    low_memory=False, dtype=str) 
                    if len(df.columns) > 1:
                        return self.normalizar(df, ano, trimestre)
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
                except Exception:
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
                'ValorDespesas': pd.to_numeric(df[col_valor].astype(str).str.replace(',', '.'), errors='coerce')
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
        # Validação de duplicados via Chunks com Tipagem Estrita
        if not self.csv_final.exists():
            return
            
        logger.info("Mapeando duplicados (Processamento em Chunks)...")
        mapa_cnpj_raz = {}
        chunksize = 100000 
        
        # Mapear CNPJ -> Razões com DTYPE str para manter integridade
        for chunk in pd.read_csv(self.csv_final, chunksize=chunksize, 
                                usecols=['CNPJ', 'RazaoSocial'], dtype={'CNPJ': str, 'RazaoSocial': str}):
            for cnpj, razao in zip(chunk['CNPJ'], chunk['RazaoSocial']):
                if pd.isna(cnpj): continue
                if cnpj not in mapa_cnpj_raz:
                    mapa_cnpj_raz[cnpj] = {str(razao)}
                else:
                    mapa_cnpj_raz[cnpj].add(str(razao))
        
        cnpjs_dup = {cnpj for cnpj, razoes in mapa_cnpj_raz.items() if len(razoes) > 1}
        
        if cnpjs_dup:
            temp_path = self.csv_final.with_suffix('.tmp')
            # Limpa resíduos de execuções anteriores
            if temp_path.exists(): temp_path.unlink() 
            
            logger.info(f"Marcando {len(cnpjs_dup)} CNPJs com múltiplas razões sociais...")
            primeiro = True
            for chunk in pd.read_csv(self.csv_final, chunksize=chunksize, dtype={'CNPJ': str}):
                mask = chunk['CNPJ'].isin(cnpjs_dup)
                chunk.loc[mask, 'StatusValidacao'] = 'CNPJ_MULTIPLAS_RAZOES'
                
                # 'w' no primeiro chunk para garantir arquivo novo, 'a' nos demais
                modo = 'w' if primeiro else 'a'
                chunk.to_csv(temp_path, mode=modo, index=False, header=primeiro, encoding='utf-8')
                primeiro = False
            
            temp_path.replace(self.csv_final)

    def gerar_relatorio_final(self):
        # Geração de relatório detalhado com contagem de status
        if not self.csv_final.exists():
            return
            
        logger.info("Gerando relatório final...")
        report_path = self.output_dir / "relatorio.txt"
        
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
        # Geração do ZIP final de entrega
        if self.csv_final.exists():
            zip_path = self.output_dir / "consolidado_despesas.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(self.csv_final, self.csv_final.name)
            return zip_path
        return None

    def executar(self):
        # Fluxo principal de execução
        logger.info("INICIANDO PIPELINE TESTE 1")
        if self.csv_final.exists(): self.csv_final.unlink()
        
        for ano, tri in self.buscar_trimestres():
            zips = self.baixar_arquivos(ano, tri)
            for z in zips:
                self.processar_e_salvar_incremental(z, ano, tri)
        
        self.aplicar_validacao_duplicados_incremental()
        self.gerar_relatorio_final()
        
        entrega = self.gerar_zip_entrega()
        if entrega: logger.info(f"✓ TESTE 1 CONCLUÍDO! Ficheiro gerado em: {entrega}")

if __name__ == "__main__":
    ANSIntegration().executar()
    
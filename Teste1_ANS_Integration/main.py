import zipfile
import logging
import requests
import pandas as pd
import urllib3
import shutil
from pathlib import Path
from bs4 import BeautifulSoup

# Desabilita avisos SSL apenas para a API da ANS (Bypass necessário para endpoints governamentais)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ANSIntegration:
    # Pipeline de integração com tratamento de Registro ANS, CNPJ e segurança Zip-Slip.
    BASE_URL = "https://dadosabertos.ans.gov.br/FTP/PDA/demonstracoes_contabeis/"
    
    def __init__(self):
        self.output_dir = Path("output")
        self.temp_dir = Path("temp")
        self.output_dir.mkdir(exist_ok=True)
        self.temp_dir.mkdir(exist_ok=True)
        self.headers = {'User-Agent': 'Mozilla/5.0'}
        self.csv_final = self.output_dir / "consolidado_despesas.csv"
        self.dtypes = {
            'CNPJ': str, 
            'RazaoSocial': str, 
            'Trimestre': str, 
            'Ano': str, 
            'StatusValidacao': str
        }

    def buscar_trimestres(self):
        # Retorna uma lista de trimestres disponíveis (ano, trimestre)
        return [('2024', '3'), ('2024', '2'), ('2024', '1')]

    def baixar_arquivos(self, ano, trimestre):
        # Baixa arquivos ZIP do site da ANS para o ano e trimestre especificados
        url_ano = f"{self.BASE_URL}{ano}/"
        logger.info(f"Buscando arquivos em {url_ano}...")
        baixados = []
        
        try:
            # verify=False é utilizado devido a instabilidades de CA nos endpoints da ANS
            res = requests.get(url_ano, headers=self.headers, verify=False, timeout=30)
            res.raise_for_status() 
            
            soup = BeautifulSoup(res.text, 'html.parser')
            padrao = f"{trimestre}T{ano}".upper()
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('.zip') and padrao in href.upper():
                    local = self.temp_dir / f"{ano}_Q{trimestre}_{href}"
                    logger.info(f"Baixando: {href}")
                    
                    with requests.get(url_ano + href, headers=self.headers, verify=False, timeout=180, stream=True) as r:
                        r.raise_for_status()
                        with open(local, 'wb') as f:
                            for chunk in r.iter_content(chunk_size=8192):
                                if chunk: f.write(chunk)
                    baixados.append(local)
            return baixados
        except Exception as e:
            logger.error(f"Erro no download: {e}")
            return []

    def processar_e_salvar_incremental(self, zip_path, ano, trimestre):
        # Processa o arquivo ZIP e salva os dados no CSV final de forma incremental
        logger.info(f"Processando incrementalmente: {zip_path.name}")
        extract_path = self.temp_dir / zip_path.stem
        
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                base_path = extract_path.resolve()
                for member in z.infolist():
                    member_path = (extract_path / member.filename).resolve()
                    # Proteção Zip-Slip com Logging
                    if base_path not in member_path.parents and member_path != base_path:
                        logger.warning(f"Proteção Zip-Slip: ignorando membro suspeito '{member.filename}'")
                        continue
                    z.extract(member, extract_path)
                
                for f in extract_path.rglob('*'):
                    if f.suffix.lower() in ['.csv', '.txt']:
                        df = self.ler_arquivo_resiliente(f, ano, trimestre)
                        if not df.empty:
                            header = not self.csv_final.exists()
                            df.to_csv(self.csv_final, mode='a', index=False, header=header, encoding='utf-8')
        finally:
            if extract_path.exists(): shutil.rmtree(extract_path)
            if zip_path.exists(): zip_path.unlink()

    def ler_arquivo_resiliente(self, path, ano, trimestre):
        # Tenta ler o arquivo com várias combinações de encoding e separadores
        for enc in ['utf-8', 'iso-8859-1', 'cp1252']:
            for sep in [';', ',', '\t']:
                try:
                    df = pd.read_csv(path, sep=sep, encoding=enc, on_bad_lines='skip', low_memory=False, dtype=str)
                    if len(df.columns) > 1:
                        return self.normalizar(df, ano, trimestre)
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
                except Exception as e:
                    if isinstance(e, (KeyboardInterrupt, SystemExit)): raise
                    continue
        return pd.DataFrame()

    def normalizar(self, df, ano, trimestre):
        # Normaliza o DataFrame para o formato padrão
        df.columns = df.columns.str.strip().str.upper()
        col_cnpj = next((c for c in df.columns if any(x in c for x in ['CNPJ', 'REG_ANS', 'REGISTRO'])), None)
        col_valor = next((c for c in df.columns if any(x in c for x in ['VL_SALDO', 'VALOR', 'DESPESA'])), None)
        col_razao = next((c for c in df.columns if any(x in c for x in ['RAZAO', 'NOME', 'OPERADORA'])), None)

        if col_cnpj and col_valor:
            es_cnpj_real = 'CNPJ' in col_cnpj.upper()
            cnpj_limpo = df[col_cnpj].astype(str).str.replace(r'\D', '', regex=True).replace('', pd.NA)
            valor_num = pd.to_numeric(
                df[col_valor].astype(str).str.replace('.', '', regex=False).str.replace(',', '.', regex=False), 
                errors='coerce'
            )

            df_res = pd.DataFrame({
                'CNPJ': cnpj_limpo,
                'RazaoSocial': df[col_razao].astype(str).str.strip() if col_razao else "N/A",
                'Trimestre': str(trimestre).zfill(2),
                'Ano': str(ano),
                'ValorDespesas': valor_num
            })
            
            df_res = df_res.dropna(subset=['CNPJ', 'ValorDespesas'])
            df_res['StatusValidacao'] = 'OK'
            
            # Valida o tamanho apenas se a coluna de origem for um CNPJ real (14 dígitos)
            if es_cnpj_real:
                df_res.loc[df_res['CNPJ'].str.len() != 14, 'StatusValidacao'] = 'CNPJ_INVALIDO'
            
            df_res.loc[df_res['ValorDespesas'] == 0, 'StatusValidacao'] = 'VALOR_ZERADO'
            df_res.loc[df_res['ValorDespesas'] < 0, 'StatusValidacao'] = 'VALOR_NEGATIVO'
            df_res.loc[df_res['RazaoSocial'].isin(['N/A', '', 'nan']), 'StatusValidacao'] = 'RAZAO_VAZIA'
            
            return df_res
        return pd.DataFrame()
    
    def aplicar_validacao_duplicados_incremental(self):
        # Aplica validação de CNPJs com múltiplas razões sociais
        if not self.csv_final.exists(): return
        logger.info("Mapeando duplicados com tipagem estrita...")
        
        mapa_cnpj_raz = {}
        chunksize = 100000 
        
        for chunk in pd.read_csv(self.csv_final, chunksize=chunksize, usecols=['CNPJ', 'RazaoSocial'], dtype=str):
            for cnpj, razao in zip(chunk['CNPJ'], chunk['RazaoSocial']):
                if pd.isna(cnpj): continue
                if cnpj not in mapa_cnpj_raz:
                    mapa_cnpj_raz[cnpj] = {str(razao)}
                else:
                    mapa_cnpj_raz[cnpj].add(str(razao))
        
        cnpjs_dup = {cnpj for cnpj, razoes in mapa_cnpj_raz.items() if len(razoes) > 1}
        
        if cnpjs_dup:
            temp_path = self.csv_final.with_suffix('.tmp')
            primeiro = True
            for chunk in pd.read_csv(self.csv_final, chunksize=chunksize, dtype=self.dtypes):
                mask = chunk['CNPJ'].isin(cnpjs_dup)
                chunk.loc[mask, 'StatusValidacao'] = 'CNPJ_MULTIPLAS_RAZOES'
                modo = 'w' if primeiro else 'a'
                chunk.to_csv(temp_path, mode=modo, index=False, header=primeiro, encoding='utf-8')
                primeiro = False
            temp_path.replace(self.csv_final)

    def gerar_relatorio_final(self):
        # Gera o relatório final de análise crítica
        if not self.csv_final.exists(): return
        logger.info("Gerando relatório final...")
        report_path = self.output_dir / "relatorio.txt"
        
        status_counts = {}
        total = 0
        for chunk in pd.read_csv(self.csv_final, chunksize=100000, usecols=['StatusValidacao'], dtype=str):
            total += len(chunk)
            counts = chunk['StatusValidacao'].value_counts().to_dict()
            for s, c in counts.items():
                status_counts[s] = status_counts.get(s, 0) + c

        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("="*60 + "\nRELATÓRIO DE ANÁLISE CRÍTICA - TESTE 1\n" + "="*60 + "\n\n")
            f.write(f"Total de registros consolidados: {total}\n\n")
            f.write("INCONSISTÊNCIAS ENCONTRADAS:\n")
            for status, count in status_counts.items():
                f.write(f"  {status}: {count}\n")

    def executar(self):
        # Execução do pipeline completo
        logger.info("INICIANDO PIPELINE TESTE 1")
        if self.csv_final.exists(): self.csv_final.unlink()
        for ano, tri in self.buscar_trimestres():
            zips = self.baixar_arquivos(ano, tri)
            for z in zips:
                self.processar_e_salvar_incremental(z, ano, tri)
        self.aplicar_validacao_duplicados_incremental()
        self.gerar_relatorio_final()
        if self.csv_final.exists():
            zip_out = self.output_dir / "consolidado_despesas.zip"
            with zipfile.ZipFile(zip_out, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(self.csv_final, self.csv_final.name)

if __name__ == "__main__":
    ANSIntegration().executar()
    
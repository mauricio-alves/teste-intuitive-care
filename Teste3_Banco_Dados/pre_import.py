import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os

def preparar_ambiente():
    # Função para preparar o ambiente baixando o arquivo CSV mais recente
    temp_path = "temp/"
    os.makedirs(temp_path, exist_ok=True)
    MAX_BYTES = 50 * 1024 * 1024 
    
    urls = [
        "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/",
        "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude/"
    ]
    
    print("🚀 Preparando ambiente para Teste 3...")
    for url_base in urls:
        downloaded_bytes = 0
        try:
            response = requests.get(url_base, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            links = [urljoin(url_base, a['href']) for a in soup.find_all('a', href=True) if a['href'].endswith('.csv')]
            
            if links:
                links.sort()
                url_dl = links[-1]
                if urlparse(url_dl).netloc != "dadosabertos.ans.gov.br":
                    print(f"⚠️ Domínio não autorizado: {url_dl}")
                    continue
                print(f"📥 Descarregando cadastro: {url_dl}")
                
                with requests.get(url_dl, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(os.path.join(temp_path, "operadoras_cadastro.csv"), 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            downloaded_bytes += len(chunk)
                            if downloaded_bytes > MAX_BYTES:
                                raise Exception("Arquivo de operadoras excede o limite de segurança.")
                            f.write(chunk)
                print("✅ Cadastro pronto para importação.")
                return
        except Exception as e:
            print(f"❌ Erro ao acessar {url_base}: {e}")
            continue
            
    print("⚠️ Aviso: Não foi possível baixar o cadastro. Verifique a conexão.")

if __name__ == "__main__":
    try:
        preparar_ambiente()
    except Exception as e:
        print(f"❌ Falha crítica na execução: {e}")
        import sys
        sys.exit(1) 
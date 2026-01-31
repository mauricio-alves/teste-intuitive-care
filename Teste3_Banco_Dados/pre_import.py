import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import os

def preparar_ambiente():
    # Criar diretório temporário
    temp_path = "temp/"
    os.makedirs(temp_path, exist_ok=True)
    
    urls = [
        "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude_ativas/",
        "https://dadosabertos.ans.gov.br/FTP/PDA/operadoras_de_plano_de_saude/"
    ]
    
    print("🚀 Preparando ambiente para Teste 3...")
    for url_base in urls:
        try:
            response = requests.get(url_base, timeout=20)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            links = [urljoin(url_base, a['href']) for a in soup.find_all('a', href=True) if a['href'].endswith('.csv')]
            
            if links:
                url_dl = links[-1]
                print(f"📥 Descarregando cadastro: {url_dl}")
                with requests.get(url_dl, stream=True) as r:
                    r.raise_for_status()
                    with open(os.path.join(temp_path, "operadoras_cadastro.csv"), 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)
                print("✅ Cadastro pronto para importação.")
                return
        except Exception as e:
            continue
    print("⚠️ Aviso: Não foi possível baixar o cadastro. Verifique a conexão.")

if __name__ == "__main__":
    preparar_ambiente()
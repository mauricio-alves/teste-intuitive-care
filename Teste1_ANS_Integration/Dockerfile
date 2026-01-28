FROM python:3.11-slim

WORKDIR /app

# Instala dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código
COPY . .

# Cria diretórios de saída
RUN mkdir -p output temp

# Comando padrão
CMD ["python", "main.py"]

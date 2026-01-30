FROM python:3.11-slim-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m appuser

COPY . .

RUN mkdir -p output temp && \
    chown -R appuser:appuser /app && \
    chmod -R 775 output temp

USER appuser

CMD ["python", "main.py"]

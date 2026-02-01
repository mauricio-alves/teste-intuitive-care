# Backend - API ANS Operadoras

> FastAPI server para fornecer dados de operadoras de planos de saúde

## 🚀 Execução Rápida

### Opção 1: Docker (Recomendado)

```bash
# Build e execução completa
docker-compose up --build

# Ou build manual
docker build -t ans-api-backend .

# Executar conectando ao PostgreSQL do host (Teste 3)
docker run -p 8000:8000 --add-host=host.docker.internal:host-gateway -e DB_HOST=host.docker.internal -e DB_PORT=5432 -e DB_NAME=ans_dados -e DB_USER=postgres -e DB_PASSWORD=postgres ans-api-backend

# Executar com hot reload (desenvolvimento)
docker run -p 8000:8000 --add-host=host.docker.internal:host-gateway -v ${PWD}/app:/app/app:ro -e DB_HOST=host.docker.interna -e DB_PORT=5432 -e DB_NAME=ans_dados -e DB_USER=postgres -e DB_PASSWORD=postgres ans-api-backend

# Ver logs
docker-compose logs -f api

# Parar
docker-compose down
```

**Acessos:**

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

**Notas:**

- O container conecta ao PostgreSQL do Teste 3 rodando no **host**
- `host.docker.internal` aponta para o localhost da máquina host
- No **Linux**, use `--add-host=host.docker.internal:host-gateway`
- No **Windows/Mac**, `host.docker.internal` funciona automaticamente

---

### Opção 2: Python Local

```bash
# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas credenciais

# Executar servidor
python main.py
```

**Acessos:**

- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

---

## 📋 Rotas da API

| Método | Rota                              | Descrição                      |
| ------ | --------------------------------- | ------------------------------ |
| GET    | `/api/operadoras`                 | Lista operadoras com paginação |
| GET    | `/api/operadoras/{cnpj}`          | Detalhes de uma operadora      |
| GET    | `/api/operadoras/{cnpj}/despesas` | Histórico de despesas          |
| GET    | `/api/estatisticas`               | Estatísticas agregadas         |
| GET    | `/api/despesas-por-uf`            | Despesas por UF (gráfico)      |

---

## 🔧 Trade-offs Técnicos

### 4.2.1. Framework: FastAPI ✅

**Escolha:** FastAPI

**Justificativa:**

| Critério                 | Flask       | FastAPI               | Decisão       |
| ------------------------ | ----------- | --------------------- | ------------- |
| **Performance**          | ⭐⭐        | ⭐⭐⭐                | FastAPI vence |
| **Validação automática** | ❌ Manual   | ✅ Pydantic           | FastAPI vence |
| **Documentação**         | ❌ Manual   | ✅ Auto (Swagger)     | FastAPI vence |
| **Tipos**                | ❌          | ✅ Type hints nativos | FastAPI vence |
| **Async/await**          | ⚠️ Complexo | ✅ Nativo             | FastAPI vence |
| **Manutenibilidade**     | ⭐⭐        | ⭐⭐⭐                | FastAPI vence |

**Conclusão:** FastAPI é superior para APIs modernas

---

### 4.2.2. Paginação: Offset-based ✅

**Escolha:** Offset-based

**Justificativa:**

| Abordagem        | Prós                           | Contras                                | Decisão      |
| ---------------- | ------------------------------ | -------------------------------------- | ------------ |
| **Offset-based** | Simples, permite pular páginas | Performance degrada em offsets grandes | ✅ Escolhida |
| Cursor-based     | Performance constante          | Não permite pular páginas              | ❌           |
| Keyset           | Rápido, escalável              | Complexo, requer ordenação fixa        | ❌           |

**Motivos:**

- Dataset pequeno (~1.500 operadoras)
- Performance aceitável com índices
- UX melhor (navegação direta para página N)
- Implementação simples

**Código:**

```python
offset = (page - 1) * limit
query = "... LIMIT %s OFFSET %s"
```

---

### 4.2.3. Cache: 5 minutos em memória ✅

**Escolha:** Cache em memória com TTL de 5 minutos

**Justificativa:**

| Abordagem           | Pros                     | Contras                     | Decisão      |
| ------------------- | ------------------------ | --------------------------- | ------------ |
| Calcular sempre     | Sempre atualizado        | Lento, sobrecarga DB        | ❌           |
| **Cache 5min**      | Rápido, reduz carga 90%+ | Pequena defasagem           | ✅ Escolhida |
| Pré-calcular tabela | Muito rápido             | Complexidade, sincronização | ❌           |

**Motivos:**

- Dados mudam raramente (importações esporádicas)
- Query de estatísticas é pesada (~2-5s)
- Usuários aceitam defasagem de até 5min
- Reduz carga no banco em 90%+

---

### 4.2.4. Estrutura de Resposta: Dados + Metadados ✅

**Escolha:** Dados + Metadados

**Justificativa:**

| Abordagem        | Exemplo                      | Pros             | Contras              | Decisão      |
| ---------------- | ---------------------------- | ---------------- | -------------------- | ------------ |
| Apenas dados     | `[{...}, {...}]`             | Simples          | Falta info paginação | ❌           |
| **Dados + meta** | `{data: [...], meta: {...}}` | Completo, padrão | Verboso              | ✅ Escolhida |

**Motivos:**

- Frontend precisa de `total`, `total_pages`, `has_next`, `has_prev`
- Facilita implementação de UI (botões, indicadores)
- Padrão REST comum
- Não adiciona overhead significativo

**Estrutura:**

```json
{
  "data": [
    {"id": 1, "razao_social": "...", ...}
  ],
  "meta": {
    "page": 1,
    "limit": 10,
    "total": 1500,
    "total_pages": 150,
    "has_next": true,
    "has_prev": false
  }
}
```

## 📊 Dependências

- **FastAPI:** Framework web moderno
- **Uvicorn:** ASGI server
- **Psycopg2:** Driver PostgreSQL
- **Pydantic:** Validação de dados

---

## 🔒 Segurança

- CORS configurado para frontend específico
- Validação automática com Pydantic
- Sanitização de inputs SQL (parametrização)
- Rate limiting (futuro: adicionar middleware)

---

## ⚡ Performance

| Endpoint               | Sem Cache | Com Cache | Melhoria |
| ---------------------- | --------- | --------- | -------- |
| `/api/estatisticas`    | ~3s       | ~50ms     | 60x      |
| `/api/despesas-por-uf` | ~1.5s     | ~30ms     | 50x      |
| `/api/operadoras`      | ~200ms    | N/A       | -        |

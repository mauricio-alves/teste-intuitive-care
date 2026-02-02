# 🏥 TESTE INTUITIVE CARE - ANS Operadoras de Saúde

> Projeto completo de análise e visualização de dados de operadoras de planos de saúde da ANS (Agência Nacional de Saúde Suplementar)

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.4+-brightgreen.svg)](https://vuejs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

---

## 📋 Visão Geral

Este projeto implementa um **pipeline completo de análise de dados** da ANS, desde a extração e transformação de dados até a visualização em uma interface web moderna. O sistema processa **2,1+ milhões de registros** de despesas de operadoras de planos de saúde, oferecendo insights através de uma API RESTful e interface web interativa.

### 🎯 Objetivos

- ✅ **Extração e Integração de Dados** via API REST da ANS
- ✅ **Transformação e Agregação** com Pandas
- ✅ **Armazenamento Estruturado** em PostgreSQL normalizado (3NF)
- ✅ **API RESTful** com FastAPI e documentação Swagger
- ✅ **Interface Web** moderna com Vue.js + TypeScript
- ✅ **Documentação Técnica** completa com justificativas de trade-offs

---

## 🗂️ Estrutura do Projeto

```
TESTE-INTUITIVE-CARE/
├── Teste1_ANS_Integration/     # Pipeline ETL Python
├── Teste2_Transformacao/        # Agregação com Pandas
├── Teste3_Banco_Dados/          # PostgreSQL + Docker
├── Teste4_API_Web/              # FastAPI + Vue.js
│   ├── backend/                 # API RESTful
│   └── frontend/                # Interface Web
└── README.md                    # Este arquivo
```

---

## 📦 Testes Implementados

### [Teste 1 - Pipeline ETL e Integração com API ANS](./Teste1_ANS_Integration/)

**Objetivo:** Extrair dados de despesas consolidadas da API REST da ANS e processar 2,1+ milhões de registros.

**Tecnologias:**

- Python 3.11+
- Requests (HTTP client)
- Pandas (processamento)
- Docker + Docker Compose

**Principais Features:**

- ✅ Extração via API REST com paginação automática
- ✅ Tratamento robusto de erros e timeouts
- ✅ Processamento de 2.119.622 registros
- ✅ Validação de dados e tipos
- ✅ Geração de CSV consolidado (1,5GB)

**Documentação:** [📖 README Teste 1](./Teste1_ANS_Integration/README.md)

---

### [Teste 2 - Transformação e Agregação de Dados](./Teste2_Transformacao/)

**Objetivo:** Transformar e agregar despesas consolidadas por operadora, trimestre e ano usando Pandas.

**Tecnologias:**

- Python 3.11+
- Pandas (transformação)
- NumPy (cálculos)
- Docker + Docker Compose

**Principais Features:**

- ✅ Agregação por operadora, ano e trimestre
- ✅ Cálculo de estatísticas (média, soma, desvio padrão)
- ✅ Geração de CSV agregado (773 operadoras únicas)
- ✅ Tratamento de valores ausentes e outliers
- ✅ Validação de integridade dos dados

**Documentação:** [📖 README Teste 2](./Teste2_Transformacao/README.md)

---

### [Teste 3 - Banco de Dados PostgreSQL](./Teste3_Banco_Dados/)

**Objetivo:** Modelar e popular banco de dados relacional normalizado (3NF) com os dados processados.

**Tecnologias:**

- PostgreSQL 14
- pgAdmin 4 (administração)
- Python 3.11+ (importação)
- Docker + Docker Compose

**Principais Features:**

- ✅ Modelo normalizado em 3FN (3 tabelas)
- ✅ Importação de 2.119.622 registros
- ✅ Índices otimizados para performance
- ✅ 4 queries analíticas implementadas
- ✅ Validação de integridade referencial
- ✅ Containers Docker prontos para produção

**Documentação:** [📖 README Teste 3](./Teste3_Banco_Dados/README.md)

---

### [Teste 4 - API RESTful e Interface Web](./Teste4_API_Web/)

**Objetivo:** Criar API REST completa e interface web para consulta e visualização dos dados.

**Tecnologias:**

- **Backend:** FastAPI, Uvicorn, PostgreSQL, Pydantic
- **Frontend:** Vue.js 3, TypeScript, Vite, Chart.js, Axios
- Docker + Docker Compose

**Principais Features:**

#### Backend (FastAPI)

- ✅ 6 rotas RESTful com documentação Swagger
- ✅ Paginação offset-based
- ✅ Busca por razão social ou CNPJ
- ✅ Cache em memória (5 min) - melhoria de >300x
- ✅ Pool de conexões (1-20 simultâneas)
- ✅ Background tasks para otimização
- ✅ Validação automática com Pydantic

**Documentação:** [📖 README Backend](./Teste4_API_Web/backend/README.md)

#### Frontend (Vue.js + TypeScript)

- ✅ Listagem paginada de operadoras
- ✅ Busca com debounce (500ms)
- ✅ Gráfico de despesas por UF (Chart.js)
- ✅ Página de detalhes com histórico
- ✅ Composables para gerenciamento de estado
- ✅ Interceptors Axios avançados
- ✅ Loading global e tratamento de erros

**Documentação:** [📖 README Frontend](./Teste4_API_Web/frontend/README.md)

#### Coleção Postman

- ✅ 6 rotas documentadas
- ✅ Exemplos de requisições e respostas
- ✅ Variáveis configuradas
- ✅ Casos de sucesso e erro

**Download:** [📥 Coleção Postman](./Teste4_API_Web/ANS_Operadoras_API.postman_collection.json)

---

## 🚀 Execução Rápida

### Pré-requisitos

- Docker 20.10+
- Docker Compose 2.0+
- Git

### Executar Teste Específico

```bash
# Teste 1 - Pipeline ETL
cd Teste1_ANS_Integration
docker-compose up --build

# Teste 2 - Transformação
cd Teste2_Transformacao
docker-compose up --build

# Teste 3 - Banco de Dados
cd Teste3_Banco_Dados
docker-compose up --build

# Teste 4 - API + Web
cd Teste4_API_Web
docker-compose up --build
# Acesse: http://localhost:5173 (Frontend)
# Acesse: http://localhost:8000/docs (API Swagger)
```

---

## 📊 Dados Processados

| Métrica                | Valor            |
| ---------------------- | ---------------- |
| **Registros Totais**   | 2.119.622        |
| **Operadoras Únicas**  | 773              |
| **Período**            | 2024 (T1 a T3)   |
| **Total de Despesas**  | R$ 17,3 trilhões |
| **Média por Registro** | R$ 8,2 milhões   |
| **Estados (UFs)**      | 27               |

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                        TESTE 1                              │
│  ┌─────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   API ANS   │ -> │ Pipeline ETL │ -> │ CSV (1.5GB)  │   │
│  └─────────────┘    └──────────────┘    └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│                        TESTE 2                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ CSV (1.5GB)  │ -> │    Pandas    │ -> │ CSV Agregado │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│                        TESTE 3                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │ CSV Agregado │ -> │  PostgreSQL  │ <- │   pgAdmin    │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                      (3 tabelas - 3NF)                      │
└─────────────────────────────────────────────────────────────┘
                               ↓
┌─────────────────────────────────────────────────────────────┐
│                        TESTE 4                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    BACKEND                          │   │
│  │  ┌──────────────┐    ┌──────────────┐              │   │
│  │  │  PostgreSQL  │ <- │   FastAPI    │              │   │
│  │  └──────────────┘    └──────────────┘              │   │
│  │         ↑                   ↓                       │   │
│  │      (Pool)            (Cache 5min)                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↓ API REST                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   FRONTEND                          │   │
│  │  ┌──────────────┐    ┌──────────────┐              │   │
│  │  │   Vue.js 3   │ -> │   Chart.js   │              │   │
│  │  └──────────────┘    └──────────────┘              │   │
│  │  (TypeScript + Composables)                         │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📈 Performance

| Componente            | Métrica         | Valor                    |
| --------------------- | --------------- | ------------------------ |
| **Pipeline ETL**      | Processamento   | ~30 min (2,1M registros) |
| **Pandas Agregação**  | Transformação   | ~5 min                   |
| **PostgreSQL Import** | Carga de Dados  | ~10 min                  |
| **API (sem cache)**   | Estatísticas    | ~3s                      |
| **API (com cache)**   | Estatísticas    | <10ms (>300x)            |
| **Frontend**          | First Load      | ~500ms                   |
| **Frontend**          | Page Navigation | ~100ms                   |

---

## 🛠️ Tecnologias Utilizadas

### Backend

- **Python 3.11+** - Linguagem principal
- **FastAPI** - Framework web moderno
- **Pandas** - Análise e transformação de dados
- **PostgreSQL 14** - Banco de dados relacional
- **Docker** - Containerização

### Frontend

- **Vue.js 3** - Framework progressivo
- **TypeScript** - Tipagem estática
- **Vite** - Build tool
- **Chart.js** - Gráficos interativos
- **Axios** - Cliente HTTP

### DevOps

- **Docker Compose** - Orquestração de containers
- **pgAdmin 4** - Administração PostgreSQL
- **Postman** - Testes de API

---

## 📄 Licença

Este projeto foi desenvolvido como parte de um teste técnico para a **Intuitive Care**.

---

## 👤 Autor

**Desenvolvido por [Maurício Oliveira Alves](https://www.linkedin.com/in/mauricio-oliveira-alves/)**

Data de Conclusão: 02 de Fevereiro de 2026

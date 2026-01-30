# Teste 3 - Banco de Dados e Análise

> Processo Seletivo - Intuitive Care | Estágio em Desenvolvimento

## 📋 Objetivo

Estruturar banco de dados relacional para armazenar dados da ANS, implementar importação dos CSVs gerados nos Testes 1 e 2, e desenvolver queries analíticas para extração de insights.

---

## 🚀 Execução Rápida

### Pré-requisitos

- CSVs dos Testes 1 e 2:
  - `consolidado_despesas.csv` (Teste 1)
  - `despesas_agregadas.csv` (Teste 2)
  - `operadoras_cadastro.csv` (Teste 2)

### Opção 1: Docker (Recomendado)

```bash
# Garante que o container do Teste 2 esteja ativo primeiro
docker-compose -f ../Teste2_Transformacao/docker-compose.yml run -d --name teste2_transformacao_container teste2-transformacao tail -f /dev/null

# Copia e executa o script de preparação
docker cp pre_import.py teste2_transformacao_container:/app/pre_import.py
docker exec -it teste2_transformacao_container python pre_import.py

# Subir o banco de dados
docker-compose up -d

# Executar a estrutura (DDL)
docker exec -it ans_db_container psql -U postgres -d ans_dados -f /scripts/01_ddl_postgresql.sql

# Importar dados (Consolida T1 e T2)
docker exec -it ans_db_container psql -U postgres -d ans_dados -f /scripts/02_import_postgresql.sql

# Executar queries analíticas
docker exec -it ans_db_container psql -U postgres -d ans_dados -f /scripts/03_queries_analiticas.sql

# Gerar relatório final (Opcional)
docker exec ans_db_container psql -U postgres -d ans_dados -f /scripts/03_queries_analiticas.sql -P border=2 -P footer=on > scripts/relatorio_final.txt

# Limpar o banco (Opcional)
docker exec -it ans_db_container psql -U postgres -d ans_dados -f /scripts/99_limpeza.sql
```

### Opção 2: MySQL

```bash
# Criar banco
mysql -u root -p -e "CREATE DATABASE ans_dados CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# Executar DDL
mysql -u root -p ans_dados < scripts/01_ddl_mysql.sql

# Importar dados
mysql -u root -p ans_dados < scripts/02_import_mysql.sql

# Executar queries analíticas
mysql -u root -p ans_dados < scripts/03_queries_analiticas.sql
```

---

## 🗂️ Estrutura de Arquivos

```
Teste3_Banco_Dados/
├── README.md                          ✅ Este arquivo
├── scripts/
│   ├── 01_ddl_postgresql.sql          ✅ Criação de tabelas (PostgreSQL)
│   ├── 01_ddl_mysql.sql               ✅ Criação de tabelas (MySQL)
│   ├── 02_import_postgresql.sql       ✅ Importação CSVs (PostgreSQL)
│   ├── 02_import_mysql.sql            ✅ Importação CSVs (MySQL)
│   ├── 03_queries_analiticas.sql      ✅ Queries analíticas
│   └── 99_limpeza.sql                 ✅ Drop tables
├── data/
│   └── .gitkeep                       ✅ Pasta para CSVs
└── docs/
    └── diagrama_er.md                 ✅ Diagrama ER
```

---

## 🔧 Decisões Técnicas e Trade-offs

### 3.2 Estrutura de Tabelas

#### **Trade-off 1: Normalização**

| Decisão         | Estratégia            | Justificativa                          |
| --------------- | --------------------- | -------------------------------------- |
| **Estrutura**   | **Normalizada (3NF)** | Reduz redundância, facilita manutenção |
| **Alternativa** | Desnormalizada        | Performance leitura, mas duplicação    |

**Estratégia Escolhida:** **Tabelas Normalizadas Separadas**

**Justificativa:**

- ✅ **Volume:** 2M+ registros - normalização reduz espaço (~30%)
- ✅ **Atualizações:** Cadastro de operadoras muda - update em 1 tabela só
- ✅ **Integridade:** FKs garantem consistência
- ✅ **Análises:** JOINs são eficientes com índices corretos
- ⚠️ **Trade-off:** Queries mais complexas, mas ganho em manutenibilidade

**Estrutura:**

```
operadoras (1) ----< (N) despesas_consolidadas
operadoras (1) ----< (N) despesas_agregadas
```

**Alternativa Considerada:**

| Abordagem      | Prós                         | Contras                    | Escolha |
| -------------- | ---------------------------- | -------------------------- | ------- |
| Normalizada    | Sem redundância, manutenível | JOINs necessários          | ✅      |
| Desnormalizada | Leitura rápida               | Duplicação, inconsistência | ❌      |
| Híbrida        | Balanced                     | Complexidade gestão        | ❌      |

---

#### **Trade-off 2: Tipos de Dados**

**Valores Monetários:**

| Tipo               | Precisão      | Performance | Escolha            |
| ------------------ | ------------- | ----------- | ------------------ |
| **DECIMAL(15,2)**  | ✅ Exata      | Média       | ✅ **Escolhida**   |
| FLOAT              | ❌ Aproximada | Rápida      | ❌                 |
| INTEGER (centavos) | ✅ Exata      | Rápida      | ⚠️ Boa alternativa |

**Decisão:** `DECIMAL(15,2)`

**Justificativa:**

- ✅ **Precisão decimal:** Valores financeiros exigem precisão exata
- ✅ **Padrão contábil:** 2 casas decimais
- ✅ **Range adequado:** Até 999 trilhões (suficiente)
- ❌ **FLOAT rejeitado:** Erros de arredondamento inaceitáveis
- ⚠️ **INTEGER (centavos):** Válido, mas DECIMAL mais legível

**Datas:**

| Tipo      | Formato             | Fuso Horário | Escolha          |
| --------- | ------------------- | ------------ | ---------------- |
| **DATE**  | YYYY-MM-DD          | Não          | ✅ **Escolhida** |
| VARCHAR   | Flexível            | Não          | ❌               |
| TIMESTAMP | YYYY-MM-DD HH:MM:SS | Sim          | ⚠️ Desnecessário |

**Decisão:** `DATE`

**Justificativa:**

- ✅ **Tipo nativo:** Validação automática
- ✅ **Funções SQL:** DATE_TRUNC, EXTRACT
- ✅ **Espaço:** 4 bytes vs 10+ VARCHAR
- ❌ **VARCHAR rejeitado:** Sem validação, dificulta queries
- ⚠️ **TIMESTAMP:** Overhead desnecessário (não precisa hora)

---

### 3.3 Importação de CSVs

#### **Tratamento de Inconsistências**

| Problema                 | Estratégia                        | Justificativa        |
| ------------------------ | --------------------------------- | -------------------- |
| **NULL em obrigatórios** | Rejeitar linha                    | Integridade > volume |
| **String em numérico**   | Tentar conversão, depois rejeitar | Máxima recuperação   |
| **Datas inconsistentes** | Conversão múltiplos formatos      | Resiliência          |
| **Encoding**             | UTF-8 explícito                   | Evita corrupção      |

**Abordagens Detalhadas:**

1. **Valores NULL em campos obrigatórios** (ex: CNPJ, ValorDespesas)
   - **Estratégia:** Rejeitar registro
   - **Justificativa:** Dados incompletos comprometem análises
   - **Implementação:** `NOT NULL` constraints + validação pré-import

2. **Strings em campos numéricos** (ex: "N/A" em ValorDespesas)
   - **Estratégia:** Tentar `CAST`, se falhar → rejeitar
   - **Justificativa:** Preserva dados válidos, descarta inválidos
   - **Implementação:** `NULLIF` + `CAST` com tratamento de erro

3. **Datas em formatos variados** (ex: "2024-03-31", "31/03/2024")
   - **Estratégia:** Conversão com múltiplos formatos
   - **Justificativa:** Dados da ANS podem ter formatos mistos
   - **Implementação:** `TO_DATE` com `COALESCE` de formatos

**Log de Erros:**

```sql
-- Tabela de importação com erros
CREATE TABLE import_errors (
    id SERIAL PRIMARY KEY,
    tabela VARCHAR(100),
    linha_original TEXT,
    erro TEXT,
    data_import TIMESTAMP DEFAULT NOW()
);
```

---

### 3.4 Queries Analíticas

#### **Query 1: Crescimento Percentual**

**Desafio:** Operadoras sem dados em todos os trimestres

**Estratégia Escolhida:** **Exigir dados no 1º e último trimestre**

**Justificativa:**

- ✅ Crescimento = (Final - Inicial) / Inicial
- ✅ Sem 1º OU último → cálculo impossível
- ✅ Trimestres intermediários → não afetam cálculo
- ⚠️ Trade-off: Exclui operadoras novas/descontinuadas

**Alternativas:**

| Abordagem                       | Prós            | Contras           | Escolha |
| ------------------------------- | --------------- | ----------------- | ------- |
| Exigir 1º e último              | Cálculo correto | Exclui algumas    | ✅      |
| Usar qualquer 2 trimestres      | Inclui mais     | Não é início→fim  | ❌      |
| Interpolar trimestres faltantes | Máxima inclusão | Dados artificiais | ❌      |

---

#### **Query 2: Distribuição por UF**

**Desafio Adicional:** Média por operadora em cada UF

**Abordagem:** Window functions + GROUP BY

**Trade-off:**

| Método               | Legibilidade | Performance    | Escolha |
| -------------------- | ------------ | -------------- | ------- |
| **Window Functions** | Alta         | Ótima          | ✅      |
| Subqueries           | Média        | Ruim (n scans) | ❌      |
| Multiple queries     | Alta         | Manual         | ❌      |

**Justificativa:**

- ✅ 1 scan da tabela
- ✅ Cálculos em paralelo
- ✅ Código conciso

---

#### **Query 3: Operadoras Acima da Média**

**Trade-off Técnico:** Múltiplas abordagens possíveis

| Abordagem        | Performance | Manutenibilidade | Legibilidade | Escolha |
| ---------------- | ----------- | ---------------- | ------------ | ------- |
| **CTE + Window** | ⭐⭐⭐      | ⭐⭐⭐           | ⭐⭐⭐       | ✅      |
| Subqueries       | ⭐⭐        | ⭐⭐             | ⭐           | ❌      |
| Temp tables      | ⭐⭐⭐      | ⭐               | ⭐⭐         | ❌      |
| Self-join        | ⭐          | ⭐               | ⭐           | ❌      |

**Estratégia Escolhida:** **CTE (Common Table Expression) + Window Functions**

**Justificativa:**

- ✅ **Performance:** 1 scan + índice na média
- ✅ **Manutenibilidade:** Fácil adicionar trimestres
- ✅ **Legibilidade:** Estrutura clara (média → comparação → count)
- ✅ **Escalabilidade:** Funciona com 3 ou 30 trimestres

**Implementação:**

```sql
WITH media_geral AS (
    SELECT AVG(valor) as media FROM despesas
),
acima_media AS (
    SELECT operadora_id, trimestre,
           CASE WHEN valor > (SELECT media FROM media_geral) THEN 1 ELSE 0 END as acima
    FROM despesas
)
SELECT operadora_id, SUM(acima) as trimestres_acima
FROM acima_media
GROUP BY operadora_id
HAVING SUM(acima) >= 2;
```

---

## 📊 Esquema do Banco

### Diagrama ER

```
┌─────────────────────────────┐
│      operadoras             │
├─────────────────────────────┤
│ ⚿ id (PK)                   │
│   registro_ans              │
│   cnpj                      │
│   razao_social              │
│   modalidade                │
│   uf                        │
└─────────────────────────────┘
           │
           │ 1
           │
           ├────────────────────┐
           │                    │
           │ N                  │ N
           ▼                    ▼
┌──────────────────────┐  ┌──────────────────────┐
│ despesas_consolidadas│  │  despesas_agregadas  │
├──────────────────────┤  ├──────────────────────┤
│ ⚿ id (PK)            │  │ ⚿ id (PK)            │
│ ⚷ operadora_id (FK)  │  │ ⚷ operadora_id (FK)  │
│   trimestre          │  │   total_despesas     │
│   ano                │  │   media_despesas     │
│   valor_despesas     │  │   desvio_padrao      │
│   data_registro      │  │   qtd_registros      │
└──────────────────────┘  └──────────────────────┘
```

### Índices Criados

| Tabela                | Índice               | Tipo   | Justificativa           |
| --------------------- | -------------------- | ------ | ----------------------- |
| operadoras            | `idx_cnpj`           | UNIQUE | Busca rápida, unicidade |
| operadoras            | `idx_registro_ans`   | INDEX  | Join comum              |
| despesas_consolidadas | `idx_operadora_trim` | INDEX  | Queries analíticas      |
| despesas_consolidadas | `idx_data`           | INDEX  | Filtros temporais       |
| despesas_agregadas    | `idx_operadora`      | INDEX  | Aggregations            |

---

## ⚡ Performance Esperada

| Operação               | Tempo Esperado | Volume         |
| ---------------------- | -------------- | -------------- |
| DDL (criação)          | ~1s            | 3 tabelas      |
| Import consolidadas    | ~30-60s        | 2.1M registros |
| Import agregadas       | ~1s            | 781 registros  |
| Query 1 (crescimento)  | ~2-5s          | 2.1M registros |
| Query 2 (distribuição) | ~1-3s          | Com índices    |
| Query 3 (acima média)  | ~3-7s          | CTE otimizado  |

---

## 🎯 Tecnologias

- **PostgreSQL 14+** (Recomendado) - Window functions, CTEs avançadas
- **MySQL 8.0+** (Alternativa) - Compatibilidade, mas sem algumas features
- **Scripts SQL** - DDL, DML, DQL separados
- **UTF-8** - Encoding consistente

---

## 📝 Observações

### Diferenças PostgreSQL vs MySQL

| Feature              | PostgreSQL    | MySQL             |
| -------------------- | ------------- | ----------------- |
| **COPY**             | ✅ Nativo     | ❌ Usar LOAD DATA |
| **Window Functions** | ✅ Completo   | ✅ 8.0+           |
| **CTEs**             | ✅ Recursivas | ✅ Não recursivas |
| **RETURNING**        | ✅            | ❌                |
| **Arrays**           | ✅            | ❌                |

**Recomendação:** PostgreSQL para análises complexas.

---

## 🔍 Validação

### Checklist de Importação

```sql
-- Verificar contagens
SELECT 'operadoras' as tabela, COUNT(*) FROM operadoras
UNION ALL
SELECT 'consolidadas', COUNT(*) FROM despesas_consolidadas
UNION ALL
SELECT 'agregadas', COUNT(*) FROM despesas_agregadas;

-- Verificar integridade referencial
SELECT COUNT(*) as orphans
FROM despesas_consolidadas dc
LEFT JOIN operadoras o ON dc.operadora_id = o.id
WHERE o.id IS NULL;

-- Verificar valores NULL indevidos
SELECT COUNT(*) as nulls_invalidos
FROM despesas_consolidadas
WHERE valor_despesas IS NULL;
```

### Resultados Esperados

| Tabela                | Registros Esperados |
| --------------------- | ------------------- |
| operadoras            | ~1.000-1.500        |
| despesas_consolidadas | ~2.100.000          |
| despesas_agregadas    | ~781                |

---

**Desenvolvido para Intuitive Care** 🚀

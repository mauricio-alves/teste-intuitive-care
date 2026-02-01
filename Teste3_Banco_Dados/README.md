# Teste 3 - Banco de Dados e Análise

> Processo Seletivo - Intuitive Care | Estágio em Desenvolvimento

## 📋 Objetivo

Estruturar banco de dados relacional para armazenar dados da ANS, implementar importação dos CSVs gerados nos Testes 1 e 2, e desenvolver queries analíticas para extração de insights.

---

## 🚀 Execução Rápida

### Pré-requisitos

O Teste 3 atua como o integrador final, dependendo dos artefatos gerados nos testes anteriores. Certifique-se de que os seguintes arquivos estão presentes em seus respectivos diretórios antes de iniciar:

- **Do Teste 1**: `Teste1_ANS_Integration/output/consolidado_despesas.csv` (Mapeado via volume como `/input_t1`)
- **Do Teste 2**: `Teste2_Transformacao/output/despesas_agregadas.csv` (Mapeado via volume como `/input_t2_out`)
- **Cadastro ANS**: `Teste3_Banco_Dados/temp/operadoras_cadastro.csv` (Baixado automaticamente pelo `pre_import.py`)

> **Nota sobre o Cadastro**: O arquivo de cadastro das operadoras é obtido diretamente dos Dados Abertos da ANS através do script `pre_import.py`. Este arquivo é armazenado temporariamente na pasta `temp/` e mapeado para o banco de dados como `/input_t2_temp` para garantir que a importação utilize a versão mais recente disponível.

### Configuração de Credenciais

1. **Copie o arquivo de exemplo**: `cp .env.example .env`
2. **Edite o .env**: Defina valores para `POSTGRES_USER`, `POSTGRES_DB` e `POSTGRES_PASSWORD`. O Docker Compose falhará se estiverem vazios.
3. **Localização**: Certifique-se de que o arquivo `.env` está localizado na raiz da pasta `Teste3_Banco_Dados`.

### Opção 1: Docker (Recomendado)

```bash
# Garantir que o container temporário do Teste 2 esteja ativo primeiro
docker-compose -f ../Teste2_Transformacao/docker-compose.yml run -d --name teste2_transformacao_container teste2-transformacao tail -f /dev/null

# Copiar e executar o script de preparação
docker cp pre_import.py teste2_transformacao_container:/app/pre_import.py
docker exec -it teste2_transformacao_container python pre_import.py

# Parar e remover o container temporário do Teste 2
docker stop teste2_transformacao_container
docker rm teste2_transformacao_container

# Subir o banco de dados
docker-compose up -d

# Executar a estrutura (DDL)
docker exec -it ans_db_container sh -c 'psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f /scripts/01_ddl_postgresql.sql'

# Importar dados (Consolida T1 e T2)
docker exec -it ans_db_container sh -c 'psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f /scripts/02_import_postgresql.sql'

# Criar índices após a carga (Melhora performance de importação)
docker exec -it ans_db_container sh -c 'psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f /scripts/03_indexes_postgresql.sql'

# Executar queries analíticas
docker exec -it ans_db_container sh -c 'psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f /scripts/04_queries_analiticas.sql --pset pager=off'

# Gerar relatório final
docker exec ans_db_container sh -c 'psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f /scripts/04_queries_analiticas.sql -P border=2 -P footer=on -o /reports/relatorio_final.txt'

# Limpar o banco (Opcional)
docker exec -it ans_db_container sh -c 'psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f /scripts/05_limpeza.sql'
```

### Opção 2: PostgreSQL (Manual/Local)

```bash
# Antes de executar os comandos abaixo, carregue as variáveis de ambiente na sua sessão de terminal
export $(grep -v '^#' .env | xargs)

# Criar o banco de dados
psql -U ${POSTGRES_USER} -c "CREATE DATABASE ${POSTGRES_DB};"

# Executar a estrutura (DDL)
psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f scripts/01_ddl_postgresql.sql

# Importar dados
psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f scripts/02_import_postgresql.sql

# Criar índices (Otimização Pós-Carga)
psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f scripts/03_indexes_postgresql.sql

# Executar queries analíticas (com pager desativado para evitar interrupção)
psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f scripts/04_queries_analiticas.sql --pset pager=off

# Gerar relatório final
psql -U ${POSTGRES_USER} -d ${POSTGRES_DB} -f scripts/04_queries_analiticas.sql -P border=2 -P footer=on -o reports/relatorio_final.txt
```

---

## 🗂️ Arquivos Gerados

Após a execução completa do workflow, as pastas de saída serão organizadas da seguinte forma para garantir o isolamento entre dados do sistema e resultados analíticos:

### 📁 `Teste3_Banco_Dados/data/` (Persistência)

- **`pgdata/`**: Diretório criado automaticamente pelo container PostgreSQL para armazenar os volumes binários e a persistência do banco de dados (2.1M+ registros).
  - _Nota: Este diretório está listado no `.gitignore` para evitar o versionamento de arquivos binários e conflitos de permissão root/user._
- **`.gitkeep`**: Arquivo de controle para preservar a pasta no repositório.

### 📁 `Teste3_Banco_Dados/reports/` (Resultados)

- **`relatorio_final.txt`**: Documento gerado pelo script de queries analíticas (`04_queries_analiticas.sql`). Contém os insights processados sobre as operadoras e despesas de 2024.
  - _Dica: Este arquivo é mapeado via Bind Mount, facilitando o acesso direto pelo host (Windows/Linux) sem necessidade de entrar no container._

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

3. **Cabeçalhos duplicados nos CSVs**
   - **Estratégia:** DELETE em tabela temporária antes do INSERT
   - **Justificativa:** Evita inserção de strings ("Registro ANS") em campos de dados
   - **Implementação:** `DELETE FROM temp_operadoras_raw WHERE linha ILIKE '%Registro ANS%'`

**Log de Erros:**

```sql
-- Tabela de suporte para logs de importação
CREATE TABLE import_errors (
    id SERIAL PRIMARY KEY,
    tabela_destino VARCHAR(100),
    linha_csv TEXT,
    erro TEXT,
    data_import TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

### 3.4 Queries Analíticas

#### **Query 1: Crescimento Percentual**

**Desafio:** Operadoras sem dados em todos os trimestres

**Estratégia Escolhida:** **Comparar o 1º vs último trimestre disponível de 2024 para cada operadora**

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

**Abordagem:** Consumo de Tabela Agregada (Data Mart) integrada do Teste 2

**Trade-off:**

| Método                                          | Legibilidade | Performance | Escolha |
| ----------------------------------------------- | ------------ | ----------- | ------- |
| **Uso de Tabela de Agregados (Materialização)** | Alta         | Máxima      | ✅      |
| Agregação direta                                | Alta         | Ótima       | ⚠️      |
| Window Functions                                | Média        | Boa         | ⚠️      |
| Subqueries                                      | Baixa        | Ruim        | ❌      |

**Justificativa:**

- ✅ **Otimização de I/O**: Em vez de realizar um scan em 2 milhões de registros, a query lê apenas ~760 linhas pré-agregadas.
- ✅ **Separação de Preocupações**: O cálculo pesado de agregação foi realizado na fase de transformação (ETL/Teste 2), deixando o banco apenas com a tarefa de exibição rápida.
- ✅ **Performance Sub-segundo**: Resultados obtidos em menos de 0.1s, ideal para dashboards e relatórios de BI.
- ✅ **Consistência Cross-Test**: Demonstra a integração funcional entre os artefatos de saída do Teste 2 e a estrutura de dados do Teste 3.

---

#### **Query 3: Operadoras Acima da Média**

**Trade-off Técnico:** Múltiplas abordagens possíveis

| Abordagem     | Performance | Manutenibilidade | Legibilidade | Escolha |
| ------------- | ----------- | ---------------- | ------------ | ------- |
| **CTE + AGG** | ⭐⭐⭐      | ⭐⭐⭐           | ⭐⭐⭐       | ✅      |
| Subqueries    | ⭐⭐        | ⭐⭐             | ⭐           | ❌      |
| Temp tables   | ⭐⭐⭐      | ⭐               | ⭐⭐         | ❌      |
| Self-join     | ⭐          | ⭐               | ⭐           | ❌      |

**Estratégia Escolhida:** **CTE (Common Table Expression) + Agregação**

**Justificativa:**

- ✅ **Performance:** 1 scan + índice na média
- ✅ **Manutenibilidade:** Fácil adicionar trimestres
- ✅ **Legibilidade:** Estrutura clara (média → comparação → count)
- ✅ **Escalabilidade:** Funciona com 3 ou 30 trimestres

---

## 📊 Esquema do Banco

### Diagrama ER

O modelo relacional detalhado (entidade-relacionamento) descrevendo as chaves primárias, estrangeiras, relacionamentos e justificativas de modelagem entre as tabelas de operadoras e despesas pode ser visualizado no link abaixo:

👉 **[Ver Diagrama de Entidade-Relacionamento (ER)](docs/diagrama_er.md)**

### Índices Criados

| Tabela                | Índice                             | Tipo         | Justificativa       |
| --------------------- | ---------------------------------- | ------------ | ------------------- |
| operadoras            | `cnpj` (constraint)                | UNIQUE       | Garante unicidade   |
| operadoras            | `registro_ans` (constraint)        | UNIQUE       | Garante unicidade   |
| operadoras            | `idx_operadoras_uf`                | INDEX        | Análises por estado |
| despesas_consolidadas | `idx_despesas_operadora_trimestre` | INDEX (comp) | Queries analíticas  |
| despesas_consolidadas | `idx_despesas_data`                | INDEX        | Filtros temporais   |
| despesas_consolidadas | `idx_despesas_valor`               | INDEX        | Ordenações          |
| despesas_agregadas    | `idx_agregadas_operadora`          | INDEX        | JOINs               |
| despesas_agregadas    | `idx_agregadas_uf`                 | INDEX        | Análises por UF     |
| despesas_agregadas    | `idx_agregadas_total`              | INDEX (DESC) | Top N queries       |

**Nota:** Constraints `UNIQUE` nas colunas `cnpj` e `registro_ans` criam índices únicos automaticamente no PostgreSQL.

---

## ⚡ Performance Esperada

| Operação               | Tempo Esperado | Volume                    |
| ---------------------- | -------------- | ------------------------- |
| DDL (criação)          | ~1s            | 4 tabelas                 |
| Import consolidadas    | ~13-14min      | 2.05M registros           |
| Import agregadas       | ~1s            | 768 registros             |
| Criação de Índices     | ~3.6s          | 9 índices                 |
| Query 1 (crescimento)  | <1s            | 2.05M registros           |
| Query 2 (distribuição) | <0.1s          | 768 registros (agregados) |
| Query 3 (acima média)  | ~1-2s          | CTE otimizado             |

> **Nota**: Testes realizados em ambiente Docker utilizando volumes mapeados. A performance das queries pode variar levemente dependendo das especificações de hardware (CPU/SSD) disponíveis para o container..

---

## 🎯 Tecnologias

- **Docker & Docker Compose** (Recomendado) - Containerização e orquestração
- **PostgreSQL 14+** - Window functions, CTEs avançadas
- **Python 3.11** - Script de preparação de ambiente
- **Scripts SQL** - DDL, DML, DQL separados
- **UTF-8** - Encoding consistente

---

## 📝 Observações Importantes

### Dados de Teste e Saneamento

- **Dados Reais**: Utilização de dados oficiais da ANS (2024, trimestres 1-3).
- **Volume Processado**: 2.119.622 registros lidos, resultando em 2.058.994 registros importados após saneamento de dados (remoção de valores negativos e inconsistências).
- **Operadoras**: 1.110 operadoras ativas cadastradas com sucesso via ON CONFLICT otimizado.
- **Performance**: Pipeline validado para processar milhões de linhas em menos de 15 minutos em ambiente Docker.

### Execução e Artefatos

- **Relatório Analítico**: O arquivo `reports/relatorio_final.txt` comprova a execução bem-sucedida de todas as queries, com resultados extraídos diretamente do banco de dados.
- **Persistência Isolada**: O uso de volumes nomeados garante que o estado do banco (`pgdata`) seja preservado de forma independente dos artefatos de saída.

### Reprodutibilidade e Integração

- **Workflow Integrado**: O ambiente Docker integra-se automaticamente com os outputs dos Testes 1 e 2 via Bind Mounts em modo somente leitura (:ro).
- **Ambiente Controlado**: O uso de limites de download (`MAX_BYTES`) no script de preparação garante a resiliência do ambiente em diferentes conexões.

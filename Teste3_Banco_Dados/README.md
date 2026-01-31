# Teste 3 - Banco de Dados e Análise

> Processo Seletivo - Intuitive Care | Estágio em Desenvolvimento

## 📋 Objetivo

Estruturar banco de dados relacional para armazenar dados da ANS, implementar importação dos CSVs gerados nos Testes 1 e 2, e desenvolver queries analíticas para extração de insights.

---

## 🚀 Execução Rápida

### Pré-requisitos

O Teste 3 depende dos artefatos gerados nos testes anteriores. Certifique-se de que os seguintes arquivos estão presentes em suas respectivas pastas de saída antes de iniciar:

- **Teste 1**: `Teste1_ANS_Integration/output/consolidado_despesas.csv`
- **Teste 2**: `Teste2_Transformacao/output/despesas_agregadas.csv`
- **Teste 2**: `operadoras_cadastro.csv`

> **Nota sobre o Cadastro**: O arquivo `operadoras_cadastro.csv` é baixado automaticamente pelo script de preparação `pre_import.py` durante a execução do workflow abaixo.

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
docker exec -it ans_db_container psql -U postgres -d ans_dados -f /scripts/01_ddl_postgresql.sql

# Importar dados (Consolida T1 e T2)
docker exec -it ans_db_container psql -U postgres -d ans_dados -f /scripts/02_import_postgresql.sql

# Executar queries analíticas
docker exec -it ans_db_container psql -U postgres -d ans_dados -f /scripts/03_queries_analiticas.sql --pset pager=off

# Gerar relatório final
docker exec ans_db_container psql -U postgres -d ans_dados -f /scripts/03_queries_analiticas.sql -P border=2 -P footer=on -o /var/lib/postgresql/data/relatorio_final.txt

# Limpar o banco (Opcional)
docker exec -it ans_db_container psql -U postgres -d ans_dados -f /scripts/99_limpeza.sql
```

### Opção 2: PostgreSQL (Manual/Local)

> **Aviso**: O script `02_import_postgresql.sql` utiliza caminhos absolutos do Docker (ex: `/input_t1`). Para execução local, altere os caminhos no SQL para os diretórios reais de saída do Teste 1 e Teste 2.

### Índices Criados (Nomes Alinhados ao DDL)

| Tabela                | Índice               | Justificativa     |
| --------------------- | -------------------- | ----------------- |
| despesas_consolidadas | `idx_despesas_data`  | Filtros temporais |
| despesas_consolidadas | `idx_despesas_valor` | Ordenações        |

```bash
# Criar o banco de dados
psql -U postgres -c "CREATE DATABASE ans_dados;"

# Executar a estrutura (DDL)
psql -U postgres -d ans_dados -f scripts/01_ddl_postgresql.sql

# Importar dados
psql -U postgres -d ans_dados -f scripts/02_import_postgresql.sql

# Executar queries analíticas
psql -U postgres -d ans_dados -f scripts/03_queries_analiticas.sql

# Gerar relatório final
psql -U postgres -d ans_dados -f scripts/03_queries_analiticas.sql -P border=2 -P footer=on -o data/relatorio_final.txt
```

---

## 🗂️ Arquivos Gerados

Após a execução completa do workflow, a estrutura da pasta `Teste3_Banco_Dados/data/` será populada e organizada da seguinte forma:

- **`pgdata/`**: Diretório criado automaticamente pelo container PostgreSQL para armazenar os volumes binários e a persistência do banco de dados (2.1M+ registros).
  - _Nota: Este diretório está listado no `.gitignore` para evitar o versionamento de arquivos binários e conflitos de permissão root/user._
- **`relatorio_final.txt`**: Documento gerado pelo script de queries analíticas, contendo os resultados das queries.
- **`.gitkeep`**: Arquivo de controle utilizado para preservar a existência da pasta `data/` no repositório remoto, garantindo que o ambiente Docker encontre o caminho mapeado para o volume.

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
-- Tabela de importação com erros
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

**Abordagem:** Agregação direta + GROUP BY

**Trade-off:**

| Método               | Legibilidade | Performance | Escolha |
| -------------------- | ------------ | ----------- | ------- |
| **Agregação direta** | Alta         | Ótima       | ✅      |
| Window Functions     | Média        | Boa         | ⚠️      |
| Subqueries           | Baixa        | Ruim        | ❌      |

**Justificativa:**

- ✅ Agregação simples: `SUM / COUNT(DISTINCT operadora_id)`
- ✅ 1 scan da tabela com GROUP BY
- ✅ Código conciso e fácil de manter
- ✅ Performance ótima com índice em UF

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

- **Docker & Docker Compose** (Recomendado) - Containerização e orquestração
- **PostgreSQL 14+** - Window functions, CTEs avançadas
- **Python 3.11** - Script de preparação de ambiente
- **Scripts SQL** - DDL, DML, DQL separados
- **UTF-8** - Encoding consistente

---

## 📝 Observações Importantes

### Dados de Teste vs Produção

- Os dados utilizados são reais da ANS (2024, trimestres 1-3)
- Volume: 2.119.622 registros de despesas
- Operadoras: ~1.500 cadastradas
- Performance testada e validada

### Execução Verificada

O arquivo `relatorio_final.txt` comprova a execução bem-sucedida de todas as queries analíticas, com resultados reais extraídos do banco de dados contendo 2.1M+ registros.

### Reprodutibilidade

O ambiente Docker garante reprodutibilidade total do teste em qualquer máquina com Docker instalado, integrando-se automaticamente com os outputs dos Testes 1 e 2.

# Diagrama Entidade-Relacionamento (ER)

## Modelo Conceitual

```
┌─────────────────────────────────────────────────────────┐
│                      OPERADORAS                         │
│                   (Entidade Central)                    │
├─────────────────────────────────────────────────────────┤
│ ⚿ id (PK)                    SERIAL                    │
│   registro_ans               TEXT UNIQUE                │
│   cnpj                       TEXT UNIQUE                │
│   razao_social               TEXT NOT NULL              │
│   modalidade                 TEXT                       │
│   uf                         CHAR(2)                    │
│   data_cadastro              TIMESTAMP                  │
└─────────────────────────────────────────────────────────┘
                            │
                            │ 1
            ┌───────────────┴───────────────┐
            │                               │
            │ N                             │ N
            ▼                               ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│   DESPESAS_CONSOLIDADAS      │  │    DESPESAS_AGREGADAS        │
│     (Detalhamento)           │  │      (Pré-agregadas)         │
├──────────────────────────────┤  ├──────────────────────────────┤
│ ⚿ id (PK)         BIGSERIAL  │  │ ⚿ id (PK)           SERIAL   │
│ ⚷ operadora_id    INTEGER FK │  │ ⚷ operadora_id      INTEGER FK│
│   trimestre       INTEGER     │  │   uf                CHAR(2)  │
│   ano             INTEGER     │  │   total_despesas    DECIMAL  │
│   valor_despesas  DECIMAL     │  │   media_despesas    DECIMAL  │
│   data_registro   DATE        │  │   desvio_padrao     DECIMAL  │
│   validacao_*     TEXT        │  │   qtd_registros     INTEGER  │
└──────────────────────────────┘  │   data_agregacao    TIMESTAMP│
                                  └──────────────────────────────┘
```

## Cardinalidade

- **OPERADORAS** 1 → N **DESPESAS_CONSOLIDADAS**
  - Uma operadora tem muitos registros de despesas
  - Cada despesa pertence a uma única operadora

- **OPERADORAS** 1 → N **DESPESAS_AGREGADAS**
  - Uma operadora tem múltiplos agregados (um por UF)
  - Cada agregado pertence a uma única operadora

## Restrições de Integridade

### Operadoras

- **PK:** `id`
- **UNIQUE:** `cnpj`, `registro_ans`
- **CHECK:** `uf ~ '^[A-Z]{2}$'` (formato válido)
- **NOT NULL:** `razao_social`

### Despesas Consolidadas

- **PK:** `id`
- **FK:** `operadora_id` → `operadoras(id)` ON DELETE CASCADE
- **CHECK:** `trimestre BETWEEN 1 AND 4`
- **CHECK:** `ano BETWEEN 2000 AND 2100`
- **CHECK:** `valor_despesas >= 0`
- **NOT NULL:** `operadora_id`, `trimestre`, `ano`, `valor_despesas`

### Despesas Agregadas

- **PK:** `id`
- **FK:** `operadora_id` → `operadoras(id)` ON DELETE CASCADE
- **UNIQUE:** `(operadora_id, uf)` - garante 1 registro por operadora/UF
- **CHECK:** `qtd_registros > 0`
- **NOT NULL:** `operadora_id`, `uf`, `total_despesas`, `qtd_registros`

## Índices

### Operadoras

```sql
CREATE INDEX idx_operadoras_cnpj ON operadoras(cnpj);
CREATE INDEX idx_operadoras_registro ON operadoras(registro_ans);
CREATE INDEX idx_operadoras_uf ON operadoras(uf);
```

**Justificativa:** Buscas frequentes por CNPJ/Registro ANS nos JOINs

### Despesas Consolidadas

```sql
CREATE INDEX idx_despesas_operadora_trimestre
    ON despesas_consolidadas(operadora_id, ano, trimestre);
CREATE INDEX idx_despesas_data ON despesas_consolidadas(data_registro);
CREATE INDEX idx_despesas_valor ON despesas_consolidadas(valor_despesas);
```

**Justificativa:**

- `operadora_id + ano + trimestre`: Queries de crescimento temporal
- `data_registro`: Filtros por período
- `valor_despesas`: Ordenações e comparações

### Despesas Agregadas

```sql
CREATE INDEX idx_agregadas_operadora ON despesas_agregadas(operadora_id);
CREATE INDEX idx_agregadas_uf ON despesas_agregadas(uf);
CREATE INDEX idx_agregadas_total ON despesas_agregadas(total_despesas DESC);
```

**Justificativa:**

- `operadora_id`: JOINs
- `uf`: Análises por estado
- `total_despesas DESC`: Top N queries (já ordenado)

## Tipos de Dados - Decisões

### Valores Monetários

- **Tipo:** `DECIMAL(15,2)` e `DECIMAL(18,2)`
- **Justificativa:**
  - Precisão exata (vs FLOAT com erros de arredondamento)
  - 2 casas decimais (padrão contábil)
  - Range adequado (até trilhões)

### Datas

- **Tipo:** `DATE` e `TIMESTAMP`
- **Justificativa:**
  - Tipo nativo (validação automática)
  - Funções SQL disponíveis (EXTRACT, DATE_TRUNC)
  - Menor espaço que VARCHAR (4-8 bytes vs 10+)

### Identificadores

- **CNPJ/Registro ANS:** `TEXT` (vs INTEGER)
- **Justificativa:**
  - Preserva zeros à esquerda
  - Não serão usados em operações aritméticas
  - Mais legível em queries

## Volumetria Estimada

| Tabela                | Registros      | Tamanho Estimado |
| --------------------- | -------------- | ---------------- |
| operadoras            | ~1.500         | ~500 KB          |
| despesas_consolidadas | ~2.100.000     | ~300 MB          |
| despesas_agregadas    | ~800           | ~100 KB          |
| **TOTAL**             | **~2.102.300** | **~300 MB**      |

_Estimativa considerando índices e overhead do PostgreSQL_

## Normalização

**Forma Normal:** 3FN (Terceira Forma Normal)

**Justificativa:**

- ✅ Elimina redundância (razão_social não repetida em 2M linhas)
- ✅ Facilita atualizações (update em 1 tabela)
- ✅ Garante integridade referencial
- ⚠️ Trade-off: Requer JOINs (mas com índices, performance é ótima)

**Alternativa rejeitada:** Desnormalização

- ❌ Duplicaria razão_social 2M+ vezes (~60 MB desperdiçados)
- ❌ Inconsistências se operadora mudar nome
- ✅ Leitura ligeiramente mais rápida (economiza 1 JOIN)

**Conclusão:** Normalização vence pela manutenibilidade e integridade.

\echo 'Iniciando criação de índices pós-carga...'

-- Índices Operadoras
CREATE INDEX IF NOT EXISTS idx_operadoras_uf ON operadoras(uf);

-- Índices Despesas Consolidadas (Críticos para as Queries 1 e 3)
CREATE INDEX IF NOT EXISTS idx_despesas_operadora_trimestre 
    ON despesas_consolidadas(operadora_id, ano, trimestre);
CREATE INDEX IF NOT EXISTS idx_despesas_data ON despesas_consolidadas(data_registro);
CREATE INDEX IF NOT EXISTS idx_despesas_valor ON despesas_consolidadas(valor_despesas);

-- Índices Despesas Agregadas (Crítico para a Query 2)
CREATE INDEX IF NOT EXISTS idx_agregadas_operadora ON despesas_agregadas(operadora_id);
CREATE INDEX IF NOT EXISTS idx_agregadas_uf ON despesas_agregadas(uf);
CREATE INDEX IF NOT EXISTS idx_agregadas_total ON despesas_agregadas(total_despesas DESC);

-- Índices Logs de Erro
CREATE INDEX IF NOT EXISTS idx_errors_tabela ON import_errors(tabela_destino);
CREATE INDEX IF NOT EXISTS idx_errors_data ON import_errors(data_import);

\echo '✓ Índices criados com sucesso!'
ANALYZE;
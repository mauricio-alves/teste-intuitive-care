-- ============================================================================
-- TESTE 3 - LIMPEZA
-- Remove todas as tabelas e objetos criados
-- ============================================================================

\echo '============================================================'
\echo 'LIMPANDO BANCO DE DADOS'
\echo '============================================================'

-- Drop views
DROP VIEW IF EXISTS v_despesas_completas CASCADE;

-- Drop functions
DROP FUNCTION IF EXISTS get_periodo_trimestre(INTEGER, INTEGER) CASCADE;

-- Drop tables (ordem inversa devido às FKs)
DROP TABLE IF EXISTS import_errors CASCADE;
DROP TABLE IF EXISTS despesas_agregadas CASCADE;
DROP TABLE IF EXISTS despesas_consolidadas CASCADE;
DROP TABLE IF EXISTS operadoras CASCADE;

\echo ''
\echo '✓ Todas as tabelas removidas'
\echo '✓ Views removidas'
\echo '✓ Functions removidas'
\echo ''
\echo 'Banco de dados limpo com sucesso!'

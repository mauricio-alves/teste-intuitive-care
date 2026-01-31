-- Criação de estrutura de banco de dados para análise de dados ANS
SET client_encoding = 'UTF8';
SET timezone = 'America/Sao_Paulo';

-- Tabela: operadoras (Entidade central)
CREATE TABLE IF NOT EXISTS operadoras (
    id SERIAL PRIMARY KEY,
    registro_ans TEXT UNIQUE,              
    cnpj TEXT UNIQUE,                       
    razao_social TEXT NOT NULL,            
    modalidade TEXT,                       
    uf CHAR(2),                                    
    data_cadastro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_uf CHECK (uf ~ '^[A-Z]{2}$')   
);

-- Índices para performance
CREATE INDEX IF NOT EXISTS idx_operadoras_uf ON operadoras(uf);

COMMENT ON TABLE operadoras IS 'Cadastro de operadoras de planos de saúde da ANS';
COMMENT ON COLUMN operadoras.registro_ans IS 'Código único de 6 dígitos da ANS';
COMMENT ON COLUMN operadoras.cnpj IS 'CNPJ sem formatação (apenas números)';

-- Tabela: despesas_consolidadas (Teste 1)
CREATE TABLE IF NOT EXISTS despesas_consolidadas (
    id BIGSERIAL PRIMARY KEY,
    operadora_id INTEGER NOT NULL,                 
    trimestre INTEGER NOT NULL,                    
    ano INTEGER NOT NULL,                          
    valor_despesas DECIMAL(15,2) NOT NULL,         
    data_registro DATE,                            
    validacao_cnpj TEXT,                    
    status_validacao TEXT,                   
    validacao_razao TEXT,                   
    
    CONSTRAINT fk_operadora FOREIGN KEY (operadora_id) 
        REFERENCES operadoras(id) ON DELETE CASCADE,
    CONSTRAINT chk_trimestre CHECK (trimestre BETWEEN 1 AND 4),
    CONSTRAINT chk_ano CHECK (ano BETWEEN 2000 AND 2100),
    CONSTRAINT chk_valor_positivo CHECK (valor_despesas >= 0)
);

-- Índices compostos para queries analíticas
CREATE INDEX IF NOT EXISTS idx_despesas_operadora_trimestre 
    ON despesas_consolidadas(operadora_id, ano, trimestre);
CREATE INDEX IF NOT EXISTS idx_despesas_data ON despesas_consolidadas(data_registro);
CREATE INDEX IF NOT EXISTS idx_despesas_valor ON despesas_consolidadas(valor_despesas);

COMMENT ON TABLE despesas_consolidadas IS 'Despesas detalhadas por trimestre (2.1M+ registros)';
COMMENT ON COLUMN despesas_consolidadas.valor_despesas IS 'DECIMAL para precisão exata em cálculos financeiros';
COMMENT ON COLUMN despesas_consolidadas.trimestre IS '1=Jan-Mar, 2=Abr-Jun, 3=Jul-Set, 4=Out-Dez';

-- Tabela: despesas_agregadas (Teste 2)
CREATE TABLE IF NOT EXISTS despesas_agregadas (
    id SERIAL PRIMARY KEY,
    operadora_id INTEGER NOT NULL,
    uf CHAR(2) NOT NULL,
    total_despesas DECIMAL(18,2) NOT NULL,         
    media_despesas DECIMAL(15,2),                  
    desvio_padrao DECIMAL(15,2),                   
    qtd_registros INTEGER NOT NULL,                
    data_agregacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_operadora_agregada FOREIGN KEY (operadora_id) 
        REFERENCES operadoras(id) ON DELETE CASCADE,
    CONSTRAINT chk_qtd_positiva CHECK (qtd_registros > 0),
    CONSTRAINT uq_operadora_uf UNIQUE (operadora_id, uf)  
);

-- Índices para análises
CREATE INDEX IF NOT EXISTS idx_agregadas_operadora ON despesas_agregadas(operadora_id);
CREATE INDEX IF NOT EXISTS idx_agregadas_uf ON despesas_agregadas(uf);
CREATE INDEX IF NOT EXISTS idx_agregadas_total ON despesas_agregadas(total_despesas DESC);

COMMENT ON TABLE despesas_agregadas IS 'Despesas pré-agregadas por operadora/UF (~781 registros)';
COMMENT ON COLUMN despesas_agregadas.total_despesas IS 'DECIMAL(18,2) para somas grandes sem overflow';

-- Tabela: import_errors
CREATE TABLE IF NOT EXISTS import_errors (
    id SERIAL PRIMARY KEY,
    tabela_destino VARCHAR(100),
    linha_csv TEXT,
    erro TEXT,
    data_import TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_errors_tabela ON import_errors(tabela_destino);
CREATE INDEX IF NOT EXISTS idx_errors_data ON import_errors(data_import);

COMMENT ON TABLE import_errors IS 'Log de erros durante importação de CSVs';

-- View: v_despesas_completas (JOIN pré-calculado)
CREATE OR REPLACE VIEW v_despesas_completas AS
SELECT 
    dc.id,
    dc.operadora_id,
    o.razao_social,
    o.cnpj,
    o.registro_ans,
    o.uf,
    o.modalidade,
    dc.ano,
    dc.trimestre,
    dc.valor_despesas,
    dc.data_registro
FROM despesas_consolidadas dc
INNER JOIN operadoras o ON dc.operadora_id = o.id;

COMMENT ON VIEW v_despesas_completas IS 'Join pré-calculado para análises frequentes';

-- Função: Obter período do trimestre
CREATE OR REPLACE FUNCTION get_periodo_trimestre(p_ano INTEGER, p_trimestre INTEGER)
RETURNS TEXT AS $$
BEGIN
    RETURN p_ano || '-T' || p_trimestre;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION get_periodo_trimestre(INTEGER, INTEGER) IS 'Retorna label de período (ex: 2024-T3)';

-- Listar tabelas criadas
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_catalog.pg_tables
WHERE schemaname = 'public'
    AND tablename IN ('operadoras', 'despesas_consolidadas', 'despesas_agregadas', 'import_errors')
ORDER BY tablename;

-- Listar índices criados
SELECT 
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
    AND tablename IN ('operadoras', 'despesas_consolidadas', 'despesas_agregadas', 'import_errors')
ORDER BY tablename, indexname;

\echo '✓ Estrutura de banco de dados criada com sucesso!'
\echo '✓ 4 tabelas criadas: operadoras, despesas_consolidadas, despesas_agregadas, import_errors'
\echo '✓ Índices otimizados criados'
\echo '✓ Constraints de integridade aplicadas'
\echo ''
\echo 'Próximo passo: Executar 02_import_postgresql.sql'

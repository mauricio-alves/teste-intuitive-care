SET client_encoding = 'UTF8';

\echo '============================================================'
\echo 'INICIANDO IMPORTAÇÃO DE DADOS'
\echo '============================================================'

-- 1/3 Importando cadastro de operadoras
\echo '1/3 Importando cadastro de operadoras...'
CREATE TEMP TABLE temp_operadoras_raw (linha TEXT);
\COPY temp_operadoras_raw FROM '/input_t2_temp/operadoras_cadastro.csv' WITH (FORMAT text);

-- Limpeza rigorosa: remove qualquer linha que contenha "Registro ANS" (cabeçalhos)
DELETE FROM temp_operadoras_raw WHERE linha ILIKE '%Registro ANS%';

INSERT INTO operadoras (registro_ans, cnpj, razao_social, modalidade, uf)
SELECT 
    REGEXP_REPLACE((string_to_array(linha, ';'))[1], '[^0-9]', '', 'g'), 
    REGEXP_REPLACE((string_to_array(linha, ';'))[2], '[^0-9]', '', 'g'), 
    UPPER(TRIM(BOTH '"' FROM (string_to_array(linha, ';'))[3])), 
    TRIM(BOTH '"' FROM (string_to_array(linha, ';'))[5]), 
    CASE 
        WHEN UPPER(TRIM(BOTH '"' FROM (string_to_array(linha, ';'))[11])) ~ '^[A-Z]{2}$' THEN UPPER(TRIM(BOTH '"' FROM (string_to_array(linha, ';'))[11]))
        ELSE UPPER(TRIM(BOTH '"' FROM (string_to_array(linha, ';'))[10]))
    END
FROM temp_operadoras_raw
WHERE (string_to_array(linha, ';'))[3] IS NOT NULL 
AND (string_to_array(linha, ';'))[3] NOT ILIKE '%Razão Social%' 
ON CONFLICT (cnpj) DO UPDATE SET razao_social = EXCLUDED.razao_social;

SELECT COUNT(*) as total_operadoras FROM operadoras;
DROP TABLE temp_operadoras_raw;

-- 2/3 Importando despesas consolidadas
\echo ''
\echo '2/3 Importando despesas consolidadas...'
CREATE TEMP TABLE temp_despesas (cnpj TEXT, razao TEXT, tri TEXT, ano TEXT, valor TEXT, status TEXT);
\COPY temp_despesas FROM '/input_t1/consolidado_despesas.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

INSERT INTO despesas_consolidadas (operadora_id, trimestre, ano, valor_despesas, validacao_valor)
SELECT 
    o.id,
    REGEXP_REPLACE(td.tri, '[^0-9]', '', 'g')::INTEGER,
    REGEXP_REPLACE(td.ano, '[^0-9]', '', 'g')::INTEGER,
    COALESCE(REGEXP_REPLACE(td.valor, '[^0-9.]', '', 'g'), '0')::DECIMAL(15,2),
    TRIM(td.status)
FROM temp_despesas td
-- Evita duplicidade usando apenas o Registro ANS como chave principal
INNER JOIN operadoras o ON (REGEXP_REPLACE(td.cnpj, '[^0-9]', '', 'g') = o.cnpj);
WHERE TRIM(td.tri) ~ '^[0]?[1-4]$' AND TRIM(td.ano) ~ '^[0-9]{4}$';

SELECT COUNT(*) as total_despesas_reais FROM despesas_consolidadas;
DROP TABLE temp_despesas;

-- 3/3 Importando despesas agregadas
\echo ''
\echo '3/3 Importando despesas agregadas...'
CREATE TEMP TABLE temp_agregadas (
    razao TEXT, uf TEXT, total TEXT, media TEXT, desvio TEXT, qtd TEXT
);

\COPY temp_agregadas FROM '/input_t2_out/despesas_agregadas.csv' WITH (FORMAT csv, HEADER true);

INSERT INTO despesas_agregadas (operadora_id, uf, total_despesas, media_despesas, desvio_padrao, qtd_registros)
SELECT 
    o.id, UPPER(TRIM(ta.uf)),
    NULLIF(TRIM(ta.total), '')::DECIMAL(18,2),
    NULLIF(TRIM(ta.media), '')::DECIMAL(15,2),
    NULLIF(TRIM(ta.desvio), '')::DECIMAL(15,2),
    NULLIF(TRIM(ta.qtd), '')::INTEGER
FROM temp_agregadas ta
INNER JOIN operadoras o ON (o.razao_social = UPPER(TRIM(ta.razao)))
ON CONFLICT DO NOTHING;

SELECT COUNT(*) as total_agregadas FROM despesas_agregadas;
DROP TABLE temp_agregadas;

\echo '✓ Importação concluída com sucesso!'
ANALYZE;

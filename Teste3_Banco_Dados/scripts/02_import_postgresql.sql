SET client_encoding = 'UTF8';

\echo '============================================================'
\echo 'INICIANDO IMPORTAÇÃO DE DADOS'
\echo '============================================================'

-- 1/3 Importando cadastro de operadoras
\echo '1/3 Importando cadastro de operadoras...'
TRUNCATE TABLE operadoras CASCADE;

CREATE TEMP TABLE temp_operadoras_raw (linha TEXT);
\COPY temp_operadoras_raw FROM '/input_t2_temp/operadoras_cadastro.csv' WITH (FORMAT text);

DELETE FROM temp_operadoras_raw WHERE linha ILIKE '%Registro ANS%';

CREATE TEMP TABLE parsed_operadoras_final AS
SELECT 
    NULLIF(REGEXP_REPLACE((string_to_array(linha, ';'))[1], '[^0-9]', '', 'g'), '') AS registro_ans,
    NULLIF(REGEXP_REPLACE((string_to_array(linha, ';'))[2], '[^0-9]', '', 'g'), '') AS cnpj,
    UPPER(TRIM(BOTH '"' FROM (string_to_array(linha, ';'))[3])) AS razao_social, 
    TRIM(BOTH '"' FROM (string_to_array(linha, ';'))[5]) AS modalidade, 
    CASE 
        WHEN UPPER(TRIM(BOTH '"' FROM (string_to_array(linha, ';'))[11])) ~ '^[A-Z]{2}$' 
            THEN UPPER(TRIM(BOTH '"' FROM (string_to_array(linha, ';'))[11]))
        WHEN UPPER(TRIM(BOTH '"' FROM (string_to_array(linha, ';'))[10])) ~ '^[A-Z]{2}$' 
            THEN UPPER(TRIM(BOTH '"' FROM (string_to_array(linha, ';'))[10]))
        ELSE NULL 
    END AS uf
FROM temp_operadoras_raw
WHERE (string_to_array(linha, ';'))[3] IS NOT NULL 
AND (string_to_array(linha, ';'))[3] NOT ILIKE '%Razão Social%';

-- 1. Insere/Atualiza por CNPJ
INSERT INTO operadoras (registro_ans, cnpj, razao_social, modalidade, uf)
SELECT registro_ans, cnpj, razao_social, modalidade, uf 
FROM parsed_operadoras_final 
WHERE cnpj IS NOT NULL
ON CONFLICT (cnpj) DO UPDATE SET razao_social = EXCLUDED.razao_social;

-- 2. Insere/Atualiza por Registro ANS (casos sem CNPJ)
INSERT INTO operadoras (registro_ans, cnpj, razao_social, modalidade, uf)
SELECT registro_ans, cnpj, razao_social, modalidade, uf 
FROM parsed_operadoras_final 
WHERE cnpj IS NULL AND registro_ans IS NOT NULL
ON CONFLICT (registro_ans) DO UPDATE SET razao_social = EXCLUDED.razao_social;

SELECT COUNT(*) as total_operadoras FROM operadoras;
DROP TABLE temp_operadoras_raw;
DROP TABLE parsed_operadoras_final;

-- 2/3 Importando despesas consolidadas
\echo ''
\echo '2/3 Importando despesas consolidadas...'
TRUNCATE TABLE despesas_consolidadas;

CREATE TEMP TABLE temp_despesas (id_csv TEXT, razao TEXT, tri TEXT, ano TEXT, valor TEXT, status TEXT);
\COPY temp_despesas FROM '/input_t1/consolidado_despesas.csv' WITH (FORMAT csv, HEADER true, DELIMITER ',');

INSERT INTO despesas_consolidadas (operadora_id, trimestre, ano, valor_despesas, status_validacao)
SELECT 
    o.id,
    REGEXP_REPLACE(td.tri, '[^0-9]', '', 'g')::INTEGER,
    REGEXP_REPLACE(td.ano, '[^0-9]', '', 'g')::INTEGER,
    COALESCE(NULLIF(REGEXP_REPLACE(td.valor, '[^0-9.]', '', 'g'), ''), '0')::DECIMAL(15,2),
    TRIM(td.status)
FROM (
    -- Limpa o ID uma única vez para milhões de linhas
    SELECT td.*, REGEXP_REPLACE(td.id_csv, '[^0-9]', '', 'g') AS id_clean 
    FROM temp_despesas td
) td
INNER JOIN operadoras o ON (
    CASE 
        WHEN LENGTH(td.id_clean) = 6 THEN o.registro_ans
        WHEN LENGTH(td.id_clean) = 14 THEN o.cnpj
        ELSE NULL
    END
) = td.id_clean
WHERE TRIM(td.tri) ~ '^[0]?[1-4]$' 
    AND TRIM(td.ano) ~ '^[0-9]{4}$'
    AND UPPER(TRIM(td.status)) <> 'VALOR_NEGATIVO';

SELECT COUNT(*) as total_despesas_reais FROM despesas_consolidadas;
DROP TABLE temp_despesas;

-- 3/3 Importando despesas agregadas
\echo ''
\echo '3/3 Importando despesas agregadas...'
TRUNCATE TABLE despesas_agregadas;

CREATE TEMP TABLE temp_agregadas (
    razao TEXT, uf TEXT, total TEXT, media TEXT, desvio TEXT, qtd TEXT
);

\COPY temp_agregadas FROM '/input_t2_out/despesas_agregadas.csv' WITH (FORMAT csv, HEADER true);

INSERT INTO despesas_agregadas (operadora_id, uf, total_despesas, media_despesas, desvio_padrao, qtd_registros)
SELECT 
    o.id, UPPER(TRIM(ta.uf)),
    COALESCE(NULLIF(TRIM(ta.total), ''), '0')::DECIMAL(18,2),
    NULLIF(TRIM(ta.media), '')::DECIMAL(15,2),
    NULLIF(TRIM(ta.desvio), '')::DECIMAL(15,2),
    COALESCE(NULLIF(REGEXP_REPLACE(ta.qtd, '[^0-9]', '', 'g'), ''), '0')::INTEGER
FROM temp_agregadas ta
INNER JOIN operadoras o ON (o.razao_social = UPPER(TRIM(ta.razao)))
WHERE NULLIF(REGEXP_REPLACE(TRIM(ta.qtd), '[^0-9]', '', 'g'), '') IS NOT NULL 
    AND NULLIF(REGEXP_REPLACE(TRIM(ta.qtd), '[^0-9]', '', 'g'), '')::INTEGER > 0
ON CONFLICT DO NOTHING;

SELECT COUNT(*) as total_agregadas FROM despesas_agregadas;
DROP TABLE temp_agregadas;

\echo '✓ Importação concluída com sucesso!'
ANALYZE;

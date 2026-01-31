SET client_encoding = 'UTF8';

\echo '============================================================'
\echo 'QUERIES ANALÍTICAS - RELATÓRIO FINAL'
\echo '============================================================'

-- Query 1: Crescimento
\echo ''
\echo 'Query 1: Top 5 Operadoras com maior crescimento (1º vs último trimestre disponível de 2024 por operadora)'
WITH limites AS (
    SELECT operadora_id, MIN(ano*10+trimestre) as min_p, MAX(ano*10+trimestre) as max_p
    FROM despesas_consolidadas WHERE ano = 2024 GROUP BY operadora_id
),
dados_crescimento AS (
    SELECT 
        o.razao_social, o.uf,
        SUM(CASE WHEN (dc.ano*10+dc.trimestre) = l.min_p THEN dc.valor_despesas ELSE 0 END) as v_inicial,
        SUM(CASE WHEN (dc.ano*10+dc.trimestre) = l.max_p THEN dc.valor_despesas ELSE 0 END) as v_final
    FROM despesas_consolidadas dc
    JOIN operadoras o ON dc.operadora_id = o.id
    JOIN limites l ON dc.operadora_id = l.operadora_id 
    GROUP BY o.razao_social, o.uf, l.min_p, l.max_p
    HAVING SUM(CASE WHEN (dc.ano*10+dc.trimestre) = l.min_p THEN dc.valor_despesas ELSE 0 END) > 0
)
SELECT 
    razao_social as "Operadora", uf as "UF",
    ROUND(v_inicial::NUMERIC, 2) as "Inicial (R$)",
    ROUND(v_final::NUMERIC, 2) as "Final (R$)",
    ROUND(((v_final - v_inicial) / v_inicial * 100)::NUMERIC, 2) as "Crescimento (%)"
FROM dados_crescimento
WHERE v_final > v_inicial
ORDER BY 5 DESC LIMIT 5;

-- Query 2: Distribuição por UF
\echo ''
\echo 'Query 2: Distribuição de despesas por UF (Top 5 por Volume)'
SELECT 
    o.uf as "UF",
    ROUND(SUM(dc.valor_despesas)::NUMERIC, 2) as "Total Despesas (R$)",
    COUNT(DISTINCT dc.operadora_id) as "Qtd Operadoras",
    ROUND((SUM(dc.valor_despesas) / COUNT(DISTINCT dc.operadora_id))::NUMERIC, 2) as "Média por Operadora (R$)"
FROM despesas_consolidadas dc
JOIN operadoras o ON dc.operadora_id = o.id
WHERE o.uf ~ '^[A-Z]{2}$'
GROUP BY o.uf
ORDER BY 2 DESC LIMIT 5;

-- Query 3: Acima da Média
\echo ''
\echo 'Query 3: Operadoras com despesas acima da média dos totais por operadora em 2 ou mais Trimestres de 2024'
WITH totais_op AS (
    SELECT ano, trimestre, operadora_id, SUM(valor_despesas) AS total_op_trim
    FROM despesas_consolidadas WHERE ano = 2024 GROUP BY ano, trimestre, operadora_id
),
media_trim AS (
    SELECT ano, trimestre, AVG(total_op_trim) as m_geral 
    FROM totais_op GROUP BY ano, trimestre
),
status_op AS (
    SELECT 
        t.operadora_id,
        o.razao_social, t.ano, t.trimestre,
        CASE WHEN t.total_op_trim > mt.m_geral THEN 1 ELSE 0 END as acima
    FROM totais_op t
    JOIN operadoras o ON t.operadora_id = o.id
    JOIN media_trim mt ON t.ano = mt.ano AND t.trimestre = mt.trimestre
)
SELECT razao_social as "Operadora", SUM(acima) as "Trimestres Acima da Média"
FROM status_op 
GROUP BY operadora_id, razao_social
ORDER BY 2 DESC, 1 ASC
LIMIT 10;

-- Bônus: Totais Gerais
\echo ''
\echo 'Bônus: Consolidação Geral 2024'
SELECT 
    ano as "Ano", trimestre as "Tri", 
    COUNT(DISTINCT operadora_id) as "Ops", 
    ROUND(SUM(valor_despesas)::NUMERIC, 2) as "Total (R$)"
FROM despesas_consolidadas WHERE ano = 2024 GROUP BY 1, 2 ORDER BY 1, 2;

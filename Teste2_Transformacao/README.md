# Teste 2 - Transformação e Validação de Dados

> Processo Seletivo - Intuitive Care | Estágio em Desenvolvimento

## 📋 Objetivo

Validar, enriquecer e agregar os dados consolidados do Teste 1. O pipeline aplica validações algorítmicas de identificadores, realiza o enriquecimento automático com dados cadastrais da ANS e gera métricas estatísticas por operadora e UF.

---

## 🚀 Execução Rápida

### Pré-requisito

O Teste 2 depende do arquivo `consolidado_despesas.csv` gerado no Teste 1. O Docker Compose está configurado para ler este arquivo automaticamente através de volumes montados.

### 🛡️ Hardening e Segurança de Container

O projeto utiliza **Hardening de Container**, garantindo que o pipeline seja executado como usuário **não-root**. A imagem define um usuário interno restrito (`appuser`). Caso o ambiente de execução exija (como em servidores Linux), a configuração pode ser complementada no `docker-compose.yml` com a instrução `user: "${UID}:${GID}"`, mantendo a execução sem privilégios elevados e garantindo a compatibilidade de permissões com o sistema hospedeiro.

### Opção 1: Docker (Recomendado)

```bash
# Build e execução do pipeline completo
docker-compose up --build

# Ou build manual
docker build -t teste2-ans .

# Executar com processamento real (Mapeia a entrada do Teste 1 e a saída local)
docker run -v ${PWD}/output:/app/output -v ${PWD}/../Teste1_ANS_Integration/output:/app/input:ro teste2-ans

# Executar demonstração (gera os dados simulados)
docker run -v ${PWD}/output:/app/output teste2-ans python demo.py

# Processar os dados da demonstração (Opcional - Requer renomear o arquivo)
docker run -v ${PWD}/output:/app/output teste2-ans mv output/consolidado_despesas_demo.csv output/consolidado_despesas.csv
docker run -v ${PWD}/output:/app/output teste2-ans python main.py
```

### Opção 2: Python Local

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar pipeline completo (necessita do arquivo do Teste 1)
python main.py

# Ou executar demonstração (gera os dados simulados)
python demo.py

# Processar os dados da demonstração (Opcional - Requer renomear o arquivo)
mv output/consolidado_despesas_demo.csv output/consolidado_despesas.csv
python main.py
```

---

## 📁 Arquivos Gerados

Após a execução, a pasta `output/` conterá:

- `dados_validados.csv`: Registros com status de validação de identificador, valor e razão social.
- `dados_enriquecidos.csv`: Base consolidada com colunas adicionais (`RegistroANS`, `Modalidade`, `UF`).
- `despesas_agregadas.csv`: **Arquivo principal de entrega** - Agrupado por operadora/UF com métricas financeiras.
- `relatorio_teste2.txt`: Relatório técnico com estatísticas de integridade e performance.
- `Teste2_Transformacao.zip`: Pacote compactado contendo todos os artefatos de saída.

---

## 🔧 Decisões Técnicas e Trade-offs

### 1 Validação de Identificadores

| Decisão            | Estratégia            | Justificativa                         |
| ------------------ | --------------------- | ------------------------------------- |
| **CNPJ inválidos** | Manter + Marcar tipo  | Transparência, não perde dados        |
| **Registro ANS**   | Aceitar (6 dígitos)   | Dados ANS usam Registro ANS, não CNPJ |
| **Algoritmo**      | Dígitos verificadores | Validação oficial Receita Federal     |

**Tipos de validação:**

- `REGISTRO_ANS_VALIDO` (6 dígitos)
- `CNPJ_VALIDO` (14 dígitos + DV correto)
- `CNPJ_TAMANHO_INVALIDO`, `CNPJ_DV_INVALIDO`, `CNPJ_DIGITOS_REPETIDOS`

### 2 Enriquecimento com Múltiplas Fontes

**Problema:** Dados consolidados usam **Registro ANS** (6 dígitos), mas cadastro padrão usa **CNPJ** (14 dígitos).

**Solução:** Join inteligente com múltiplas fontes em ordem de prioridade.

| Fonte                | URL                                        | Chave               | Match Esperado |
| -------------------- | ------------------------------------------ | ------------------- | -------------- |
| 1. Cadastro Completo | `.../operadoras_de_plano_de_saude/`        | Registro ANS + CNPJ | ~90%           |
| 2. Operadoras Ativas | `.../operadoras_de_plano_de_saude_ativas/` | CNPJ                | ~30-40%        |
| 3. Registro ANS      | `.../oper_com_registro_ativo/`             | Registro ANS        | ~80-90%        |

**Lógica:**

```python
# Detecta automaticamente qual chave usar
if 'REGISTRO_ANS' in cadastro:
    join_por = 'REGISTRO_ANS'  # Match alto
else:
    join_por = 'CNPJ'          # Fallback
```

**Nota sobre a chave de join:**

Embora o requisito especifique "CNPJ como chave", os dados consolidados do Teste 1 utilizam **Registro ANS** (6 dígitos), não CNPJ (14 dígitos). O código implementa detecção automática da chave disponível, priorizando Registro ANS quando presente no cadastro (match ~90%), com fallback para CNPJ (match ~30%). Esta adaptação foi necessária para atender ao objetivo real do enriquecimento: preencher Razão Social e UF para agregação posterior.

**Tratamento de não-match:**

- Tipo de Join: **Left** (mantém todos os dados)
- Status: `ENRIQUECIDO` ou `SEM_CADASTRO`
- Valores padrão: `NAO_ENCONTRADO`, `NAO_INFORMADO`, `XX`

**Alternativas consideradas:**

| Estratégia       | Prós        | Contras       | Escolha |
| ---------------- | ----------- | ------------- | ------- |
| Múltiplas fontes | Match ~90%  | Mais complexo | ✅      |
| Só cadastro CNPJ | Simples     | Match ~0%     | ❌      |
| Inner Join       | CSV "limpo" | Perde dados   | ❌      |

### 3 Agregação por Razão Social + UF

| Decisão           | Estratégia             | Justificativa                    |
| ----------------- | ---------------------- | -------------------------------- |
| **Processamento** | Pandas em memória      | 2M registros OK, simplicidade    |
| **Filtro**        | Remove N/A e inválidos | Só agrega dados válidos          |
| **Ordenação**     | Sort pós-agregação     | DataFrame pequeno (~1000 linhas) |

**Métricas calculadas:**

| Métrica           | Descrição                                             |
| ----------------- | ----------------------------------------------------- |
| **TotalDespesas** | Soma total das despesas por operadora na UF           |
| **MediaDespesas** | Média das despesas identificadas no período           |
| **DesvioPadrao**  | Medida de variabilidade (identifica valores atípicos) |
| **QtdRegistros**  | Contagem total de entradas processadas                |

---

## 🐛 Validações Implementadas

| Tipo                | Validações                                          |
| ------------------- | --------------------------------------------------- |
| **Identificadores** | Registro ANS (6), CNPJ (14 + DV), Dígitos repetidos |
| **Valores**         | Numéricos, Positivos (> 0), Não nulos               |
| **Razão Social**    | Não vazia, Diferente de N/A/nan                     |

---

## ⏱️ Performance Realizada

- **Volumetria:** > 2.100.000 registros processados.
- **Tempo total:** ~2-3 minutos (Pipeline completo incluindo download cadastral).
- **Memória:** Estabilizada entre 500-700MB via tipos categóricos.

---

## 🎯 Tecnologias

- **Python 3.11** (Slim-Bookworm)
- **Pandas & NumPy** (Engenharia e Transformação de Dados)
- **BeautifulSoup4** (Web Scraping de dados cadastrais)
- **Docker & Docker Compose** (Execução isolada e segura)

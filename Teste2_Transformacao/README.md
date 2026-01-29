# Teste 2 - Transformação e Validação de Dados

> Processo Seletivo - Intuitive Care | Estágio em Desenvolvimento

## 📋 Objetivo

Validar, enriquecer e agregar os dados consolidados do Teste 1. O pipeline aplica validações algorítmicas de identificadores, realiza o enriquecimento automático com dados cadastrais da ANS e gera métricas estatísticas por operadora e UF.

---

## 🚀 Execução Rápida

### Pré-requisito

O Teste 2 depende do arquivo `consolidado_despesas.csv` gerado no Teste 1. O Docker Compose está configurado para ler este arquivo automaticamente através de volumes montados.

### Opção 1: Docker (Recomendado)

#### 🛡️ Hardening e Segurança de Container

O projeto utiliza **Hardening de Container**, garantindo que o pipeline seja executado como usuário **não-root**. A imagem define um usuário interno restrito (`appuser`). Caso o ambiente de execução exija (como em servidores Linux), a configuração pode ser complementada no `docker-compose.yml` com a instrução `user: "${UID}:${GID}"`, mantendo a execução sem privilégios elevados e garantindo a compatibilidade de permissões com o sistema hospedeiro.

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

# Ou executar demonstração (gera e processa dados simulados)
python demo.py
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

### 1 Identificadores - Estratégia Híbrida (CNPJ e Registro ANS)

**Problema:** Os dados da ANS frequentemente utilizam o Registro ANS (6 dígitos) na coluna destinada ao CNPJ (14 dígitos).

**Estratégia Escolhida:** **Identificação Multinível**.

- O sistema valida CNPJs através do algoritmo oficial de dígitos verificadores.
- Simultaneamente, aceita identificadores de 6 dígitos como `REGISTRO_ANS_VALIDO`.
- **Prós:** Evita o descarte massivo de dados legítimos da ANS que não possuem CNPJ no log de despesas.

### 2 Enriquecimento e Join

**Tratamento de Match:** - Utilizou-se um **Left Join** para garantir que nenhuma despesa do Teste 1 seja perdida, mesmo que a operadora não conste no cadastro ativo.

- Registros sem correspondência são marcados como `SEM_CADASTRO` e preenchidos com valores padrão (`XX`, `NAO_INFORMADO`).

**Tratamento de Duplicatas:**

- Antes do join, o cadastro de operadoras é deduplicado pelo CNPJ (`drop_duplicates`) para evitar a explosão artificial de registros (Fanning-out).

### 3 Agregação e Performance

**Otimização de Memória:**

- Colunas de alta repetição (`UF`, `Modalidade`, `Ano`) são convertidas para o tipo `category`.
- O agrupamento utiliza `observed=True` para evitar falhas de índice em DataFrames esparsos ou vazios.

---

## 🐛 Validações Implementadas

### Identificadores

- ✅ Registro ANS (6 dígitos)
- ✅ CNPJ (14 dígitos com validação de dígitos verificadores)
- ✅ Detecção de dígitos repetidos e tamanhos inválidos

### Valores e Razão Social

- ✅ Numéricos Positivos (> 0)
- ✅ Razão Social não vazia (Tratamento resiliente de tipos `NaN` e `float`)

---

## 📈 Agregações Calculadas

| Métrica           | Descrição                                             |
| ----------------- | ----------------------------------------------------- |
| **TotalDespesas** | Soma total das despesas por operadora na UF           |
| **MediaDespesas** | Média das despesas identificadas no período           |
| **DesvioPadrao**  | Medida de variabilidade (identifica valores atípicos) |
| **QtdRegistros**  | Contagem total de entradas processadas                |

---

## ⏱️ Performance Realizada

- **Volumetria:** > 2.100.000 registros processados.
- **Tempo total:** ~1 minuto (Pipeline completo incluindo download cadastral).
- **Memória:** Estabilizada entre 400-600MB via tipos categóricos.

---

## 🎯 Tecnologias

- **Python 3.11** (Slim-Bookworm)
- **Pandas & NumPy** (Engenharia e Transformação de Dados)
- **BeautifulSoup4** (Web Scraping de dados cadastrais)
- **Docker & Docker Compose** (Execução isolada e segura)

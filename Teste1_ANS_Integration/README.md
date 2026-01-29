# Teste 1 - Integração com API da ANS

> Processo Seletivo - Intuitive Care | Estágio em Desenvolvimento

## 📋 Objetivo

Integrar com a API de Dados Abertos da ANS, baixar demonstrações contábeis dos últimos 3 trimestres, processar arquivos de despesas e consolidar em um único CSV.

---

## 🚀 Execução Rápida

### Opção 1: Docker (Recomendado)

#### 🛡️ Hardening e Segurança de Container

O projeto utiliza **Hardening de Container**, garantindo que o pipeline seja executado como usuário **não-root**. A imagem define um usuário interno restrito (`appuser`). Caso o ambiente de execução exija (como em servidores Linux), a configuração pode ser complementada no `docker-compose.yml` com a instrução `user: "${UID}:${GID}"`, mantendo a execução sem privilégios elevados e garantindo a compatibilidade de permissões com o sistema hospedeiro.

```bash
# Build e execução com API real
docker-compose up --build

# Ou build manual
docker build -t teste1-ans .

# Executar com API real
docker run -v ${PWD}/output:/app/output teste1-ans

# Executar demonstração (dados simulados)
docker run -v ${PWD}/output:/app/output teste1-ans python demo.py
```

### Opção 2: Python Local

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar com API real
python main.py

# Ou executar demonstração (dados simulados)
python demo.py
```

---

## 📁 Arquivos Gerados

Após execução, a pasta `output/` contém:

- `consolidado_despesas.csv`: Dados consolidados e normalizados.
- `consolidado_despesas.zip`: **Arquivo de entrega** compactado.
- `relatorio.txt`: Relatório automatizado de análise crítica e inconsistências.

---

## 📊 Estrutura do CSV

| Coluna              | Descrição                                                           |
| ------------------- | ------------------------------------------------------------------- |
| **CNPJ**            | Identificador da operadora (ou Registro ANS no Teste 1)             |
| **RazaoSocial**     | Nome da operadora (marcado como N/A para enriquecimento no Teste 2) |
| **Trimestre / Ano** | Período de competência do dado                                      |
| **ValorDespesas**   | Valor financeiro normalizado                                        |
| **StatusValidacao** | Etiqueta de integridade do registro                                 |

---

## 🔧 Decisões Técnicas e Trade-offs

### 1. Processamento: Streaming & Chunks (Escalabilidade)

Diferente de carregar arquivos inteiros na RAM, o pipeline utiliza **Streaming de Download** e **Processamento em Chunks**.

- **Por quê?** Permite processar volumes massivos de dados (Gb) mantendo o consumo de memória estável (~500MB), inclusive durante a validação de duplicados e geração de relatórios.

### 2. Segurança: Hardening e Proteção contra Injeção

- **Zip Slip Protection**: Validação rigorosa de caminhos durante a extração para evitar escrita de arquivos fora do diretório temporário.
- **Least Privilege**: O Dockerfile cria um usuário restrito, evitando que a aplicação rode como `root`.

### 3. Resiliência: Captura Granular de Erros

O código substitui blocos genéricos por capturas específicas (`RequestException`, `ParserError`, `UnicodeDecodeError`).

- **Por quê?** Evita falhas silenciosas e fornece logs precisos para depuração de problemas de rede ou encoding da ANS.

### 4. Higiene de Ambiente

Implementada a limpeza automática de diretórios e arquivos temporários (`temp/`) imediatamente após o processamento de cada ZIP.

---

## 🐛 Inconsistências Tratadas (Análise Crítica)

Todos os registros com problemas são **mantidos e marcados** na coluna `StatusValidacao` para garantir transparência total e auditabilidade:

| Status                    | Descrição                                          |
| ------------------------- | -------------------------------------------------- |
| `OK`                      | Registro íntegro                                   |
| `CNPJ_INVALIDO`           | Identificador com formato inesperado               |
| `CNPJ_MULTIPLAS_RAZOES`   | Mesmo identificador vinculado a nomes distintos    |
| `VALOR_ZERADO / NEGATIVO` | Inconsistências em valores financeiros             |
| `RAZAO_VAZIA`             | Nome da operadora ausente (comum antes do Teste 2) |

---

## ⏱️ Performance Realizada

- **Tempo (API real):** ~35 segundos (em ambiente Docker estável).
- **Registros:** > 1.000.000 de linhas processadas com sucesso.
- **Estabilidade:** Consumo de memória fixo via processamento incremental.

---

## 🎯 Tecnologias

- **Python 3.11** (Slim-Bookworm)
- **Pandas** (Data Chunks)
- **BeautifulSoup** (FTP Parsing)
- **Docker & Docker Compose** (Security Hardened)

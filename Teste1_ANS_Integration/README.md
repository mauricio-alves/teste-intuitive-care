# Teste 1 - Integração com API da ANS

> Processo Seletivo - Intuitive Care | Estágio em Desenvolvimento

## 📋 Objetivo

Integrar com a API de Dados Abertos da ANS, baixar demonstrações contábeis dos últimos 3 trimestres, processar arquivos de despesas e consolidar em um único CSV.

## 🚀 Execução Rápida

### Opção 1: Python Local

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar demonstração (dados simulados)
python demo.py

# Ou executar com API real
python main.py
```

### Opção 2: Docker

```bash
# Build
docker build -t ans-integration .

# Executar demonstração
docker run -v $(pwd)/output:/app/output ans-integration python demo.py

# Executar com API real
docker run -v $(pwd)/output:/app/output ans-integration
```

## 📁 Arquivos Gerados

Após execução, a pasta `output/` contém:

- `consolidado_despesas.csv` - Dados consolidados
- `consolidado_despesas.zip` - **Arquivo de entrega**
- `relatorio.txt` - Relatório de inconsistências

## 📊 Estrutura do CSV

```csv
CNPJ,RazaoSocial,Trimestre,Ano,ValorDespesas,StatusValidacao
12345678000190,Operadora XYZ,03,2024,150000.50,OK
98765432000111,MedCare,03,2024,0,VALOR_ZERADO
```

## 🔧 Decisões Técnicas

### Processamento: Incremental
**Por quê?** Não sobrecarrega RAM, funciona com arquivos grandes.

### Inconsistências: Manter e Marcar
**Por quê?** Transparência total. Permite auditoria. Dados podem ser corrigidos depois.

### Detecção: Automática
**Por quê?** Funciona com estruturas variadas. Resiliente a mudanças na API.

### Código: Simples
**Por quê?** É um teste de estágio. KISS (Keep It Simple, Stupid).

## 🐛 Inconsistências Tratadas

Todos os registros com problemas são **mantidos e marcados** na coluna `StatusValidacao`:

| Status | Descrição |
|--------|-----------|
| `OK` | Registro válido |
| `CNPJ_INVALIDO` | CNPJ não tem 14 dígitos |
| `CNPJ_MULTIPLAS_RAZOES` | Mesmo CNPJ com nomes diferentes |
| `VALOR_ZERADO` | Despesa = 0 |
| `VALOR_NEGATIVO` | Despesa < 0 |
| `RAZAO_VAZIA` | Nome da operadora vazio |

## ⏱️ Performance

- **Tempo:** 5-15 minutos
- **Memória:** ~500MB
- **Disco:** ~200MB

## 📝 Observações

- Use `demo.py` para testar rapidamente sem depender da API
- A API da ANS pode estar lenta ou indisponível
- Todos os registros com problemas são mantidos (não deletados)
- Filtre por `StatusValidacao == 'OK'` para dados válidos

## 🎯 Tecnologias

- Python 3.11
- Pandas (manipulação de dados)
- Requests (HTTP)
- BeautifulSoup (parsing HTML)
- Docker (containerização)

---

**Desenvolvido para Intuitive Care** 🚀

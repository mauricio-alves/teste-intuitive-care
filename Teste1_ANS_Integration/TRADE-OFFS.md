# Decisões Técnicas - Teste 1

## 🎯 Filosofia

Para um teste de **estágio**, priorizei:
- **Simplicidade** sobre complexidade
- **Clareza** sobre design patterns avançados  
- **Funcionalidade** sobre features extras
- **KISS**: Keep It Simple, Stupid

---

## 1. Processamento de Dados

### Escolha: Incremental

**Alternativas consideradas:**
- A) Carregar tudo em memória
- B) Processamento incremental (streaming)

**Por que B?**

| Critério | Opção A | Opção B |
|----------|---------|---------|
| Memória | ❌ Alta | ✅ Baixa |
| Performance | ✅ Rápida | ⚠️ Moderada |
| Escalabilidade | ❌ Limitada | ✅ Boa |
| Complexidade | ✅ Simples | ⚠️ Média |

**Contexto:** Arquivos da ANS podem ter milhões de registros. Processamento incremental evita crashes.

---

## 2. Tratamento de Inconsistências

### Escolha: Manter e Marcar

**Alternativas consideradas:**
- A) Deletar registros com problemas
- B) Corrigir automaticamente
- C) Manter e marcar

**Por que C?**

**Contra A (Deletar):**
- ❌ Perda de informação
- ❌ Não permite auditoria
- ❌ Oculta problemas da fonte

**Contra B (Corrigir):**
- ❌ Pode introduzir erros
- ❌ Assume lógica que pode estar errada

**A favor de C:**
- ✅ Transparência total
- ✅ Permite análise posterior
- ✅ Dados podem ser corrigidos na fonte
- ✅ Rastreabilidade completa

**Implementação:**
```python
df['StatusValidacao'] = 'OK'
df.loc[problema, 'StatusValidacao'] = 'TIPO_PROBLEMA'
```

---

## 3. Detecção de Colunas

### Escolha: Automática por padrões

**Alternativas consideradas:**
- A) Nomes fixos (hardcoded)
- B) Detecção automática
- C) Configuração externa (JSON/YAML)

**Por que B?**

| Critério | A | B | C |
|----------|---|---|---|
| Flexibilidade | ❌ | ✅ | ✅ |
| Manutenção | ❌ | ✅ | ⚠️ |
| Complexidade | ✅ | ⚠️ | ❌ |

**Contexto:** Arquivos da ANS variam nos nomes de colunas. Detecção automática é resiliente sem adicionar complexidade excessiva.

---

## 4. Estrutura do Código

### Escolha: Classe OOP simplificada

**Alternativas consideradas:**
- A) Script com funções
- B) Classe orientada a objetos
- C) Múltiplos módulos

**Por que B?**

**Contra A:**
- ❌ Dificulta reutilização
- ❌ Variáveis globais problemáticas

**Contra C:**
- ❌ Over-engineering para um teste
- ❌ Adiciona complexidade desnecessária

**A favor de B:**
- ✅ Organização clara
- ✅ Estado encapsulado
- ✅ Fácil de testar
- ✅ Balanceamento ideal

```python
class ANSIntegration:
    def __init__(self): ...
    def buscar_trimestres(self): ...
    def processar(self): ...
    def validar(self): ...
```

---

## 5. Logging

### Escolha: logging module

**Alternativas consideradas:**
- A) print() direto
- B) logging module
- C) Framework externo (loguru, structlog)

**Por que B?**

**Contra A:**
- ❌ Difícil desabilitar
- ❌ Sem níveis de severidade
- ❌ Não salva em arquivo

**Contra C:**
- ❌ Dependência extra
- ❌ Over-engineering

**A favor de B:**
- ✅ Níveis de log (INFO, WARNING, ERROR)
- ✅ Salva em arquivo
- ✅ Formato consistente
- ✅ Padrão Python

---

## Resumo

| Aspecto | Escolha | Razão Principal |
|---------|---------|-----------------|
| Processamento | Incremental | Escalabilidade |
| Inconsistências | Marcar | Transparência |
| Detecção | Automática | Flexibilidade |
| Estrutura | Classe OOP | Organização |
| Logs | logging | Profissionalismo |
| Complexidade | Simples | É um estágio! |

---

## Melhorias Futuras

Se fosse para **produção real**:

1. ✅ Testes unitários (pytest)
2. ✅ Validação completa de CNPJ (dígitos verificadores)
3. ✅ Cache de downloads (Redis)
4. ✅ Processamento paralelo (multiprocessing)
5. ✅ Banco de dados (PostgreSQL)
6. ✅ API para consulta (FastAPI)
7. ✅ CI/CD (GitHub Actions)

Mas para um teste de estágio, foco está em:
- ✅ Funcionalidade
- ✅ Organização
- ✅ Documentação
- ✅ Decisões justificadas

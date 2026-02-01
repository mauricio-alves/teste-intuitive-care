# Frontend - ANS Operadoras

> Interface Vue.js + TypeScript para visualização de dados de operadoras de planos de saúde

## 🚀 Execução Rápida

### Pré-requisito

- Arquivo `.env` é **OBRIGATÓRIO** ao usar Docker

### Opção 1: Docker (Recomendado)

```bash
# Build e execução completa
docker-compose up --build

# Ou build manual
docker build -t ans-frontend .

# Executar (modo desenvolvimento com hot reload)
docker run -p 5173:5173 -v ${PWD}/src:/app/src:ro -v ${PWD}/public:/app/public:ro -e VITE_API_URL=http://localhost:8000 ans-frontend

# Executar sem volumes (sem hot reload)
docker run -p 5173:5173 -e VITE_API_URL=http://localhost:8000 ans-frontend

# Ver logs
docker-compose logs -f frontend

# Parar
docker-compose down
```

**Acesso:** http://localhost:5173

**Notas:**

- O frontend conecta à API em `http://localhost:8000`
- Certifique-se de que o backend está rodando
- Volumes montados permitem hot reload (alterações refletem automaticamente)

---

### Opção 2: Node.js Local

```bash
# Instalar dependências
npm install

# Executar em desenvolvimento
npm run dev
```

**Acesso:** http://localhost:5173

**Build para produção:**

```bash
npm run build
# Arquivos gerados em: dist/

# Preview do build
npm run preview
```

---

## 📋 Funcionalidades

- ✅ Listagem paginada de operadoras
- ✅ Busca por razão social ou CNPJ
- ✅ Gráfico de distribuição de despesas por UF
- ✅ Página de detalhes com histórico de despesas
- ✅ Tratamento de erros e loading states

---

## 🔧 Trade-offs Técnicos

### 4.3.1. Busca/Filtro: Servidor ✅

**Escolha:** Busca no servidor

**Justificativa:**

| Abordagem    | Prós                       | Contras             | Decisão      |
| ------------ | -------------------------- | ------------------- | ------------ |
| **Servidor** | Escalável, payload pequeno | Latência rede       | ✅ Escolhida |
| Cliente      | Instantâneo                | Carrega todos dados | ❌           |
| Híbrido      | Melhor UX                  | Complexo            | ❌           |

**Motivos:**

- Dataset de ~1.500 operadoras é grande para carregar tudo
- Busca SQL (ILIKE) é otimizada com índices
- Payload reduzido (apenas página atual)
- Debounce de 500ms mitiga latência

---

### 4.3.2. Gerenciamento de Estado: Composables ✅

**Escolha:** Composables (Vue 3)

**Justificativa:**

| Abordagem       | Prós                    | Contras                    | Decisão      |
| --------------- | ----------------------- | -------------------------- | ------------ |
| Props/Events    | Simples                 | Dificulta compartilhamento | ❌           |
| Pinia/Vuex      | Centralizado            | Overhead para app pequeno  | ❌           |
| **Composables** | Reutilizável, type-safe | Requer Vue 3               | ✅ Escolhida |

**Motivos:**

- App pequeno (~2 páginas)
- Composables são suficientes para compartilhar lógica
- Type-safe com TypeScript
- Sem boilerplate de Pinia/Vuex
- Reatividade nativa do Vue 3

---

### 4.3.3. Performance da Tabela: Paginação Simples ✅

**Escolha:** Paginação server-side + renderização simples

**Justificativa:**

| Estratégia      | Prós                    | Contras        | Decisão      |
| --------------- | ----------------------- | -------------- | ------------ |
| **Paginação**   | Simples, performance ok | -              | ✅ Escolhida |
| Virtual Scroll  | Performance máxima      | Complexo       | ❌           |
| Infinite Scroll | UX melhor               | Memória cresce | ❌           |

**Motivos:**

- Apenas 10 itens por página (leve)
- Não justifica virtual scroll
- UX melhor com paginação tradicional (navegação direta)

---

### 4.3.4. Tratamento de Erros e Loading ✅

**Estratégia:** Estados explícitos com mensagens específicas

#### **Loading States**

```vue
<div v-if="loading" class="loading">
  <div class="spinner"></div>
  <p>Carregando operadoras...</p>
</div>
```

**Motivos:**

- Feedback visual claro
- UX melhor que conteúdo vazio
- Spinner animado

#### **Estados de Erro**

```vue
<div v-else-if="error" class="erro">
  <p>❌ {{ error }}</p>
  <button @click="recarregar">Tentar novamente</button>
</div>
```

**Trade-off: Mensagens Específicas ✅**

| Abordagem       | Prós             | Contras             | Decisão      |
| --------------- | ---------------- | ------------------- | ------------ |
| **Específicas** | Melhor debugging | Pode expor detalhes | ✅ Escolhida |
| Genéricas       | Seguro           | Menos útil          | ❌           |

**Motivos:**

- App interno (não expõe para usuários finais)
- Facilita debugging
- Melhor UX para desenvolvedores

**Exemplos de erros:**

- "Erro de conexão. Verifique se o servidor está rodando."
- "Operadora não encontrada"
- "Nenhuma despesa encontrada"

#### **Dados Vazios**

```vue
<div v-else-if="!temOperadoras" class="vazio">
  <p>Nenhuma operadora encontrada.</p>
</div>
```

**Diferença de erro:**

- Erro = problema técnico
- Vazio = sem resultados (estado válido)

---

## 🎯 Tecnologias

- **Vue.js 3:** Framework progressivo para construção de interfaces e Single Page Applications
- **TypeScript:** Tipagem estática para maior segurança, autocompletar e escalabilidade do código
- **Vite:** Ferramenta de build de próxima geração que oferece um servidor de desenvolvimento extremamente rápido
- **Axios:** Cliente HTTP baseado em promessas para comunicação com a API FastAPI
- **Chart.js:** Biblioteca versátil para a renderização do gráfico de distribuição de despesas por UF
- **Vue Router:** Gerenciador oficial de rotas para navegação entre a Home e Detalhes da Operadora

---

## 🎨 Estilo

- CSS vanilla (sem frameworks)
- Componentes scoped
- Design simples e funcional
- Sem responsividade para esse MVP

---

## ⚡ Performance Esperada

| Métrica            | Valor  |
| ------------------ | ------ |
| First Load         | ~500ms |
| Page Navigation    | ~100ms |
| API Calls (cached) | ~50ms  |
| Bundle Size        | ~200KB |

<template>
  <div class="tabela-operadoras">
    <div class="busca-container">
      <input v-model="termoBusca" @input="onBuscaChange" type="text" placeholder="Buscar por razão social ou CNPJ..." class="busca-input" />
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Carregando operadoras...</p>
    </div>

    <div v-else-if="error" class="erro">
      <p>❌ {{ error }}</p>
      <button @click="recarregar" class="btn-secundario">Tentar novamente</button>
    </div>

    <div v-else-if="!temOperadoras" class="vazio">
      <p>Nenhuma operadora encontrada.</p>
    </div>

    <div v-else class="tabela-wrapper">
      <table class="tabela">
        <thead>
          <tr>
            <th>Razão Social</th>
            <th>CNPJ</th>
            <th>UF</th>
            <th>Modalidade</th>
            <th>Total Despesas</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="op in operadoras" :key="op.id">
            <td>{{ op.razao_social }}</td>
            <td>{{ formatCNPJ(op.cnpj) }}</td>
            <td>{{ op.uf || "-" }}</td>
            <td>{{ op.modalidade || "-" }}</td>
            <td>{{ formatCurrency(op.total_despesas || 0) }}</td>
            <td>
              <button @click="verDetalhes(op.cnpj)" class="btn-primario">Ver Detalhes</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="paginacao">
        <button @click="irPagina(paginaAtual - 1)" :disabled="!temAnterior" class="btn-secundario">← Anterior</button>

        <span class="info-pagina"> Página {{ paginaAtual }} de {{ totalPaginas }} ({{ meta?.total || 0 }} operadoras) </span>

        <button @click="irPagina(paginaAtual + 1)" :disabled="!temProxima" class="btn-secundario">Próxima →</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useOperadoras } from "@/composables/useOperadoras";
import { formatCNPJ, formatCurrency, debounce } from "@/utils/formatters";

const router = useRouter();

const { operadoras, meta, loading, error, carregarOperadoras, temOperadoras, paginaAtual, totalPaginas, temProxima, temAnterior } = useOperadoras();

const termoBusca = ref("");
const paginaCorrente = ref(1);
const itensPorPagina = 10;

const onBuscaChange = debounce(() => {
  paginaCorrente.value = 1;
  carregarOperadoras(1, itensPorPagina, termoBusca.value);
}, 500);

function irPagina(pagina: number) {
  paginaCorrente.value = pagina;
  carregarOperadoras(pagina, itensPorPagina, termoBusca.value);
}

function recarregar() {
  carregarOperadoras(paginaCorrente.value, itensPorPagina, termoBusca.value);
}

function verDetalhes(cnpj: string) {
  router.push(`/operadora/${cnpj}`);
}

onMounted(() => {
  carregarOperadoras(1, itensPorPagina);
});
</script>

<style scoped>
.tabela-operadoras {
  width: 100%;
}

.busca-container {
  margin-bottom: 1.5rem;
}

.busca-input {
  width: 100%;
  padding: 0.75rem;
  font-size: 1rem;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.loading,
.erro,
.vazio {
  text-align: center;
  padding: 3rem;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.tabela-wrapper {
  overflow-x: auto;
}

.tabela {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1.5rem;
}

.tabela th,
.tabela td {
  padding: 0.75rem;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.tabela th {
  background-color: #f8f9fa;
  font-weight: 600;
}

.tabela tbody tr:hover {
  background-color: #f8f9fa;
}

.paginacao {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 0;
}

.info-pagina {
  color: #666;
}

.btn-primario {
  background-color: #3498db;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-primario:hover {
  background-color: #2980b9;
}

.btn-secundario {
  background-color: #95a5a6;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
}

.btn-secundario:hover:not(:disabled) {
  background-color: #7f8c8d;
}

.btn-secundario:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.erro {
  color: #e74c3c;
}
</style>

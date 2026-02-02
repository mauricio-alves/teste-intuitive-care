<template>
  <div class="detalhes-page">
    <button @click="voltar" class="btn-voltar">← Voltar</button>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
      <p>Carregando detalhes...</p>
    </div>

    <div v-else-if="error" class="erro">
      <p>❌ {{ error }}</p>
    </div>

    <div v-else-if="operadora && historico" class="conteudo">
      <div class="header">
        <h1>{{ operadora.razao_social }}</h1>
        <div class="info-basica">
          <span><strong>CNPJ:</strong> {{ formatCNPJ(operadora.cnpj) }}</span>
          <span><strong>UF:</strong> {{ operadora.uf || "-" }}</span>
          <span><strong>Modalidade:</strong> {{ operadora.modalidade || "-" }}</span>
        </div>
      </div>

      <div class="cards-resumo">
        <div class="card">
          <h3>Total Despesas</h3>
          <p class="valor">{{ formatCurrency(historico.soma_total) }}</p>
        </div>
        <div class="card">
          <h3>Média por Trimestre</h3>
          <p class="valor">{{ formatCurrency(historico.media) }}</p>
        </div>
        <div class="card">
          <h3>Total de Trimestres</h3>
          <p class="valor">{{ historico.total_registros }}</p>
        </div>
      </div>

      <div class="historico">
        <h2>Histórico de Despesas</h2>
        <table class="tabela">
          <thead>
            <tr>
              <th>Período</th>
              <th>Ano</th>
              <th>Trimestre</th>
              <th>Valor</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="despesa in historico.despesas" :key="despesa.periodo">
              <td>{{ despesa.periodo }}</td>
              <td>{{ despesa.ano }}</td>
              <td>T{{ despesa.trimestre }}</td>
              <td>{{ formatCurrency(despesa.valor_despesas) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { apiService } from "@/services/api";
import { formatCNPJ, formatCurrency } from "@/utils/formatters";
import type { OperadoraDetail, DespesasHistorico } from "@/types";

const route = useRoute();
const router = useRouter();

const operadora = ref<OperadoraDetail | null>(null);
const historico = ref<DespesasHistorico | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

function voltar() {
  router.push("/");
}

onMounted(async () => {
  const cnpj = route.params.cnpj as string;

  try {
    const [opData, histData] = await Promise.all([apiService.buscarOperadora(cnpj), apiService.buscarHistoricoDespesas(cnpj)]);

    operadora.value = opData;
    historico.value = histData;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Erro ao carregar detalhes";
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.detalhes-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

.btn-voltar {
  background: #95a5a6;
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: 1.5rem;
}

.btn-voltar:hover {
  background: #7f8c8d;
}

.loading,
.erro {
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

.header {
  margin-bottom: 2rem;
}

.header h1 {
  margin-bottom: 1rem;
  color: #2c3e50;
}

.info-basica {
  display: flex;
  gap: 2rem;
  color: #666;
}

.cards-resumo {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card h3 {
  margin: 0 0 0.5rem 0;
  color: #7f8c8d;
  font-size: 0.9rem;
}

.card .valor {
  font-size: 1.8rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
}

.historico {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.historico h2 {
  margin: 0 0 1.5rem 0;
  color: #2c3e50;
}

.tabela {
  width: 100%;
  border-collapse: collapse;
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
</style>

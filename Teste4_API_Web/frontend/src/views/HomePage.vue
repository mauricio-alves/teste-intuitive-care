<template>
  <div class="home-page">
    <h1>Operadoras de Planos de Saúde - ANS</h1>

    <div v-if="loading" class="loading-stats">
      <p>Carregando indicadores...</p>
    </div>

    <div v-else-if="error" class="error-stats">
      <p>⚠️ {{ error }}</p>
      <button @click="carregarEstatisticas" class="btn-retry">Tentar novamente</button>
    </div>

    <div v-else-if="estatisticas" class="cards-container">
      <div class="card">
        <h3>Total Despesas</h3>
        <p class="valor-grande">{{ formatCurrency(estatisticas.total_despesas) }}</p>
      </div>

      <div class="card">
        <h3>Operadoras</h3>
        <p class="valor-grande">{{ estatisticas.total_operadoras }}</p>
      </div>

      <div class="card">
        <h3>Média Despesas</h3>
        <p class="valor-grande">{{ formatCurrency(estatisticas.media_despesas) }}</p>
      </div>
    </div>

    <GraficoDespesasUF />

    <TabelaOperadoras />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import TabelaOperadoras from "@/components/TabelaOperadoras.vue";
import GraficoDespesasUF from "@/components/GraficoDespesasUF.vue";
import { useEstatisticas } from "@/composables/useEstatisticas";
import { formatCurrency } from "@/utils/formatters";

const { estatisticas, loading, error, carregarEstatisticas } = useEstatisticas();

onMounted(() => {
  carregarEstatisticas();
});
</script>

<style scoped>
.home-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

h1 {
  margin-bottom: 2rem;
  color: #2c3e50;
}

.cards-container {
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
  font-weight: 500;
}

.valor-grande {
  font-size: 1.8rem;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
}

.loading-stats,
.error-stats {
  padding: 2rem;
  text-align: center;
  background: white;
  border-radius: 8px;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.error-stats {
  border: 1px solid #f87171;
  color: #991b1b;
}

.btn-retry {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background-color: #ef4444;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.btn-retry:hover {
  background-color: #dc2626;
}
</style>

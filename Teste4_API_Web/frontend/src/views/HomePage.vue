<template>
  <div class="home-page">
    <h1>Operadoras de Planos de Saúde - ANS</h1>

    <div v-if="!loadingStats && estatisticas" class="cards-container">
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

const { estatisticas, loading: loadingStats, carregarEstatisticas } = useEstatisticas();

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
</style>

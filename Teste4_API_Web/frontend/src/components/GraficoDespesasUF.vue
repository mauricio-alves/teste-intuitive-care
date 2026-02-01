<template>
  <div class="grafico-container">
    <h3>Distribuição de Despesas por UF</h3>

    <div v-if="loading" class="loading">Carregando gráfico...</div>
    <div v-if="error" class="erro">{{ error }}</div>
    <div v-show="!loading && !error" style="height: 400px; position: relative">
      <canvas ref="chartCanvas"></canvas>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { Chart, registerables } from "chart.js";
import { apiService } from "@/services/api";
import { formatLargeNumber } from "@/utils/formatters";

Chart.register(...registerables);

const chartCanvas = ref<HTMLCanvasElement | null>(null);
const loading = ref(true);
const error = ref<string | null>(null);

onMounted(async () => {
  try {
    const data = await apiService.buscarDespesasPorUF();
    if (!chartCanvas.value) return;

    new Chart(chartCanvas.value, {
      type: "bar",
      data: {
        labels: data.ufs,
        datasets: [
          {
            label: "Total Despesas (R$)",
            data: data.valores,
            backgroundColor: "rgba(52, 152, 219, 0.6)",
            borderColor: "rgba(52, 152, 219, 1)",
            borderWidth: 1,
          },
        ],
      },
      options: {
        responsive: true,
        plugins: {
          legend: {
            display: true,
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                return `R$ ${formatLargeNumber(context.parsed.y)}`;
              },
            },
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: (value) => formatLargeNumber(Number(value)),
            },
          },
        },
      },
    });

    loading.value = false;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Erro ao carregar gráfico";
    loading.value = false;
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.grafico-container {
  margin: 2rem 0;
  padding: 1.5rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

h3 {
  margin-bottom: 1.5rem;
  color: #2c3e50;
}

.loading,
.erro {
  text-align: center;
  padding: 2rem;
}

.erro {
  color: #e74c3c;
}

canvas {
  max-height: 400px;
}
</style>

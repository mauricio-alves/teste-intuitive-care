import { ref } from "vue";
import { apiService } from "@/services/api";
import type { Estatisticas } from "@/types";

export function useEstatisticas() {
  const estatisticas = ref<Estatisticas | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function carregarEstatisticas() {
    loading.value = true;
    error.value = null;

    try {
      estatisticas.value = await apiService.buscarEstatisticas();
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Erro ao carregar estatísticas";
      estatisticas.value = null;
    } finally {
      loading.value = false;
    }
  }

  return {
    estatisticas,
    loading,
    error,
    carregarEstatisticas,
  };
}

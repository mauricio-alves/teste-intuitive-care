import { ref, computed } from "vue";
import { apiService } from "@/services/api";
import type { Operadora, PaginatedResponse, PaginationMeta } from "@/types";

export function useOperadoras() {
  const operadoras = ref<Operadora[]>([]);
  const meta = ref<PaginationMeta | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function carregarOperadoras(page: number = 1, limit: number = 10, busca?: string) {
    loading.value = true;
    error.value = null;

    try {
      const response: PaginatedResponse<Operadora> = await apiService.listarOperadoras(page, limit, busca);

      operadoras.value = response.data;
      meta.value = response.meta;
    } catch (err) {
      error.value = err instanceof Error ? err.message : "Erro ao carregar operadoras";
      operadoras.value = [];
      meta.value = null;
    } finally {
      loading.value = false;
    }
  }

  const temOperadoras = computed(() => operadoras.value.length > 0);
  const paginaAtual = computed(() => meta.value?.page || 1);
  const totalPaginas = computed(() => meta.value?.total_pages || 0);
  const temProxima = computed(() => meta.value?.has_next || false);
  const temAnterior = computed(() => meta.value?.has_prev || false);

  return {
    operadoras,
    meta,
    loading,
    error,
    carregarOperadoras,
    temOperadoras,
    paginaAtual,
    totalPaginas,
    temProxima,
    temAnterior,
  };
}

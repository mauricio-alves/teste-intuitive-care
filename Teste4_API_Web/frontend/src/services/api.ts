import axios from "axios";
import type { Operadora, OperadoraDetail, DespesasHistorico, Estatisticas, DespesasPorUF, PaginatedResponse } from "@/types";
import { useUI } from "@/composables/useUI";

// Configuração da instância do Axios
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

const { setLoading, setError } = useUI();

// Interceptors para gerenciar loading e erros globalmente
api.interceptors.request.use(
  (config) => {
    setLoading(true);
    return config;
  },
  (error) => {
    setLoading(false);
    return Promise.reject(error);
  },
);

api.interceptors.response.use(
  (response) => {
    setLoading(false);
    return response;
  },
  (error) => {
    setLoading(false);

    let message = "Ocorreu um erro inesperado. Tente novamente mais tarde.";

    if (error.response) {
      const apiError = error.response.data as { detail?: string };
      message = apiError.detail || `Erro ${error.response.status}: Falha na comunicação com o servidor.`;
    } else if (error.request) {
      message = "Não foi possível conectar ao servidor. Verifique sua conexão.";
    }

    setError(message);
    return Promise.reject(error);
  },
);

// Serviços da API
export const apiService = {
  async listarOperadoras(page: number = 1, limit: number = 10, busca?: string): Promise<PaginatedResponse<Operadora>> {
    const params: any = { page, limit };
    if (busca) params.busca = busca;

    const { data } = await api.get("/api/operadoras", { params });
    return data;
  },

  async buscarOperadora(cnpj: string): Promise<OperadoraDetail> {
    const { data } = await api.get(`/api/operadoras/${cnpj}`);
    return data;
  },

  async buscarHistoricoDespesas(cnpj: string): Promise<DespesasHistorico> {
    const { data } = await api.get(`/api/operadoras/${cnpj}/despesas`);
    return data;
  },

  async buscarEstatisticas(): Promise<Estatisticas> {
    const { data } = await api.get("/api/estatisticas");
    return data;
  },

  async buscarDespesasPorUF(): Promise<DespesasPorUF> {
    const { data } = await api.get("/api/despesas-por-uf");
    return data;
  },
};

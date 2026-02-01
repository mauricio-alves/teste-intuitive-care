import axios, { AxiosError } from "axios";
import type { Operadora, OperadoraDetail, DespesasHistorico, Estatisticas, DespesasPorUF, PaginatedResponse, ApiError } from "@/types";

// Configuração da instância do Axios
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

// Interceptor para tratar erros globalmente
api.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiError>) => {
    if (error.response) {
      throw new Error(error.response.data.detail || "Erro no servidor");
    } else if (error.request) {
      throw new Error("Erro de conexão. Verifique se o servidor está rodando.");
    } else {
      throw new Error("Erro desconhecido");
    }
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

import axios from "axios";
import type { Operadora, OperadoraDetail, DespesasHistorico, Estatisticas, DespesasPorUF, PaginatedResponse } from "@/types";
import { useUI } from "@/composables/useUI";

const api = axios.create({
  baseURL: "",
  timeout: 10000,
});

const { setLoading, setError } = useUI();

let pendingRequests = 0;

const handleRequest = () => {
  pendingRequests++;
  if (pendingRequests === 1) setLoading(true);
};

const handleResponse = () => {
  pendingRequests = Math.max(0, pendingRequests - 1);
  if (pendingRequests === 0) setLoading(false);
};

api.interceptors.request.use(
  (config) => {
    handleRequest();
    return config;
  },
  (error) => {
    handleResponse();
    return Promise.reject(error);
  },
);

api.interceptors.response.use(
  (response) => {
    handleResponse();
    return response;
  },
  (error) => {
    handleResponse();
    let message = "Ocorreu um erro inesperado. Tente novamente mais tarde.";

    if (error.response) {
      const apiError = error.response.data as { detail?: string };
      message = apiError.detail || `Erro ${error.response.status}: Falha na comunicação com o servidor.`;
    } else if (error.request) {
      message = "Não foi possível conectar ao servidor. Verifique sua conexão.";
    }

    setError(message);
    error.message = message;
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

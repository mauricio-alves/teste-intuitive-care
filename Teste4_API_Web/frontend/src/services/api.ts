import axios from "axios";
import type { Operadora, OperadoraDetail, DespesasHistorico, Estatisticas, DespesasPorUF, PaginatedResponse } from "@/types";
import { useUI } from "@/composables/useUI";

declare module "axios" {
  export interface AxiosRequestConfig {
    showGlobalAlert?: boolean;
    showGlobalLoading?: boolean;
  }
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
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
    if (config.showGlobalLoading !== false) {
      handleRequest();
    }
    return config;
  },
  (error) => {
    handleResponse();
    return Promise.reject(error);
  },
);

api.interceptors.response.use(
  (response) => {
    if (response.config.showGlobalLoading !== false) {
      handleResponse();
    }
    return response;
  },
  (error) => {
    if (error.config?.showGlobalLoading !== false) {
      handleResponse();
    }
    let message = "Ocorreu um erro inesperado. Tente novamente mais tarde.";

    if (error.response) {
      const detail = error.response.data?.detail;

      if (typeof detail === "string") {
        message = detail;
      } else if (Array.isArray(detail)) {
        const msgs = detail.map((item: any) => (item && typeof item.msg === "string" ? item.msg : null)).filter((msg): msg is string => !!msg);

        if (msgs.length > 0) {
          message = `Erro de validação: ${msgs.join("; ")}`;
        } else {
          message = `Erro ${error.response.status}: Dados inválidos enviados ao servidor.`;
        }
      } else {
        message = `Erro ${error.response.status}: Falha na comunicação com o servidor.`;
      }
    } else if (error.request) {
      message = "Não foi possível conectar ao servidor. Verifique sua conexão.";
    }

    if (error.config?.showGlobalAlert !== false) {
      setError(message);
    }

    error.message = message;
    return Promise.reject(error);
  },
);

// Serviços da API
export const apiService = {
  async listarOperadoras(page: number = 1, limit: number = 10, busca?: string): Promise<PaginatedResponse<Operadora>> {
    const params: { page: number; limit: number; busca?: string } = { page, limit };
    if (busca) params.busca = busca;

    const { data } = await api.get("/api/operadoras", { params, showGlobalAlert: false });
    return data;
  },

  async buscarOperadora(cnpj: string): Promise<OperadoraDetail> {
    const { data } = await api.get(`/api/operadoras/${cnpj}`, { showGlobalAlert: false });
    return data;
  },

  async buscarHistoricoDespesas(cnpj: string): Promise<DespesasHistorico> {
    const { data } = await api.get(`/api/operadoras/${cnpj}/despesas`, { showGlobalAlert: false });
    return data;
  },

  async buscarEstatisticas(): Promise<Estatisticas> {
    const { data } = await api.get("/api/estatisticas", { showGlobalAlert: false });
    return data;
  },

  async buscarDespesasPorUF(): Promise<DespesasPorUF> {
    const { data } = await api.get("/api/despesas-por-uf", { showGlobalAlert: false });
    return data;
  },
};

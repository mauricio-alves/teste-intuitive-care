import { Operadora } from "./operadora";

export interface DespesaItem {
  ano: number;
  trimestre: number;
  valor_despesas: number;
  periodo: string;
}

export interface DespesasHistorico {
  operadora: Operadora;
  despesas: DespesaItem[];
  total_registros: number;
  soma_total: number;
  media: number;
}

export interface DespesasPorUF {
  ufs: string[];
  valores: number[];
}

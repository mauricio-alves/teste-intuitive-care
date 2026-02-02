export interface Operadora {
  id: number;
  registro_ans: string | null;
  cnpj: string;
  razao_social: string;
  modalidade: string | null;
  uf: string | null;
  total_despesas?: number;
}

export interface OperadoraDetail extends Operadora {
  data_cadastro: string | null;
  total_registros: number;
  media_despesas: number;
  total_despesas: number;
}

export interface Estatisticas {
  total_despesas: number;
  media_despesas: number;
  total_operadoras: number;
  total_registros: number;
  top_5_operadoras: Array<{
    razao_social: string;
    uf: string | null;
    total_despesas: number;
  }>;
  periodo_analise: {
    ano_inicial: number;
    ano_final: number;
    trimestre_inicial: number;
    trimestre_final: number;
  };
}

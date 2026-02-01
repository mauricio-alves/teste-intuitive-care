from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class OperadoraBase(BaseModel):
    # Schema base de operadora
    id: int
    registro_ans: Optional[str]
    cnpj: str
    razao_social: str
    modalidade: Optional[str]
    uf: Optional[str]

class OperadoraListItem(OperadoraBase):
    # Item da lista de operadoras
    total_despesas: Optional[float] = Field(None, description="Total de despesas consolidadas")

class OperadoraDetailResponse(OperadoraBase):
    # Detalhes completos de uma operadora
    data_cadastro: Optional[datetime]
    total_despesas: Optional[float]
    total_registros: int
    media_despesas: Optional[float]

class DespesaItem(BaseModel):
    # Item de despesa no histórico
    ano: int
    trimestre: int
    valor_despesas: float
    periodo: str

class DespesasHistoricoResponse(BaseModel):
    # Histórico de despesas de uma operadora
    operadora: OperadoraBase
    despesas: List[DespesaItem]
    total_registros: int
    soma_total: float
    media: float

class EstatisticasResponse(BaseModel):
    # Estatísticas gerais do sistema
    total_despesas: float
    media_despesas: float
    total_operadoras: int
    total_registros: int
    top_5_operadoras: List[dict]
    periodo_analise: dict

class PaginationMeta(BaseModel):
    # Metadados de paginação
    page: int
    limit: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool

class OperadoraListResponse(BaseModel):
    # Resposta paginada genérica
    data: List[OperadoraListItem]
    meta: PaginationMeta

class DespesasPorUF(BaseModel):
    # Despesas agrupadas por UF
    ufs: List[str]
    valores: List[float]

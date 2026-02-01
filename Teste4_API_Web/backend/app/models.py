from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class OperadoraBase(BaseModel):
    id: int
    registro_ans: Optional[str] = None
    cnpj: str
    razao_social: str
    modalidade: Optional[str] = None
    uf: Optional[str] = None

    class Config:
        from_attributes = True

class OperadoraListItem(OperadoraBase):
    total_despesas: Optional[float] = Field(0.0, description="Total de despesas consolidadas")

class OperadoraDetailResponse(OperadoraBase):
    data_cadastro: Optional[datetime] = None
    total_despesas: float = 0.0
    total_registros: int = 0
    media_despesas: float = 0.0

class DespesaItem(BaseModel):
    ano: int
    trimestre: int
    valor_despesas: float = 0.0
    periodo: str

    class Config:
        from_attributes = True

class DespesasHistoricoResponse(BaseModel):
    operadora: Optional[OperadoraBase] = None
    despesas: List[DespesaItem] = []
    total_registros: int = 0
    soma_total: float = 0.0
    media: float = 0.0

class TopOperadoraItem(BaseModel):
    razao_social: str
    uf: Optional[str] = None
    total_despesas: float = 0.0

class PeriodoAnalise(BaseModel):
    ano_inicial: int = 0
    ano_final: int = 0
    trimestre_inicial: int = 0
    trimestre_final: int = 0

class EstatisticasResponse(BaseModel):
    total_despesas: float = 0.0
    media_despesas: float = 0.0
    total_operadoras: int = 0
    total_registros: int = 0
    top_5_operadoras: List[TopOperadoraItem] = []
    periodo_analise: Optional[PeriodoAnalise] = None

class PaginationMeta(BaseModel):
    page: int = 1
    limit: int = 10
    total: int = 0
    total_pages: int = 0
    has_next: bool = False
    has_prev: bool = False

class OperadoraListResponse(BaseModel):
    data: List[OperadoraListItem] = []
    meta: Optional[PaginationMeta] = None

class DespesasPorUF(BaseModel):
    ufs: List[str] = []
    valores: List[float] = []

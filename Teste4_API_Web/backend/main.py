from fastapi import FastAPI, HTTPException, Query, Path, BackgroundTasks 
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Optional
import uvicorn

from contextlib import asynccontextmanager
from app.database import get_db_connection
from app.models import (
    OperadoraDetailResponse,
    DespesasHistoricoResponse,
    EstatisticasResponse,
    OperadoraListResponse,
    DespesasPorUF
)
from app.services import OperadoraService, EstatisticasService
from app.cache import cache_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eventos de startup/shutdown
    logger.info("🚀 API iniciada com sucesso!")
    logger.info("📊 Conectando ao banco de dados...")
    try:
        from app.database import get_db_connection
        conn = get_db_connection()
        conn.close()
        logger.info("✅ Banco de dados conectado")
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao banco: {e}")
    
    yield
    logger.info("👋 API desligada")

# Criação da aplicação FastAPI com lifespan
app = FastAPI(
    title="ANS Operadoras API",
    description="API para consulta de dados de operadoras de planos de saúde",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["Content-Type", "Authorization"],
)

# Serviços
operadora_service = OperadoraService()
estatisticas_service = EstatisticasService()

# Configuração de Logs básica
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_TTL_DEFAULT = 300

@app.get("/")
async def root():
    # Raiz da API
    return {
        "message": "ANS Operadoras API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/api/operadoras", response_model=OperadoraListResponse)
async def listar_operadoras(
    # Parametros de paginação e busca
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(10, ge=1, le=100, description="Itens por página"),
    busca: Optional[str] = Query(None, description="Busca por razão social ou CNPJ")
):

    # Lista operadoras com paginação e busca
    try:
        result = operadora_service.listar_operadoras(
            page=page,
            limit=limit,
            busca=busca
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro interno ao processar lista de operadoras")

@app.get("/api/operadoras/{cnpj}", response_model=OperadoraDetailResponse)
async def detalhe_operadora(
    cnpj: str = Path(..., pattern=r"^\d{14}$", description="CNPJ da operadora (apenas 14 números)")
):
    # Retorna detalhes de uma operadora específica
    try:
        operadora = operadora_service.buscar_por_cnpj(cnpj)
        if not operadora:
            raise HTTPException(status_code=404, detail="Operadora não encontrada")
        return operadora
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro interno ao processar detalhes da operadora")

@app.get("/api/operadoras/{cnpj}/despesas", response_model=DespesasHistoricoResponse)
async def historico_despesas(
    cnpj: str = Path(..., pattern=r"^\d{14}$", description="CNPJ da operadora (apenas 14 números)")
):
    # Retorna histórico de despesas de uma operadora
    try:
        historico = operadora_service.buscar_historico_despesas(cnpj)

        if historico.get('operadora') is None:
            raise HTTPException(status_code=404, detail="Operadora não encontrada")
        
        if historico['total_registros'] == 0:
            raise HTTPException(status_code=404, detail="Nenhuma despesa encontrada para esta operadora")
        return historico
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro interno ao processar histórico")

@app.get("/api/estatisticas", response_model=EstatisticasResponse)
async def estatisticas(background_tasks: BackgroundTasks):
    # Retorna estatísticas agregadas
    cache_key = "estatisticas_gerais"
    cached = cache_manager.get(cache_key)
    background_tasks.add_task(cache_manager.cleanup_expired)

    if cached:
        return cached
    
    try:
        stats = estatisticas_service.calcular_estatisticas()
        cache_manager.set(cache_key, stats, ttl=CACHE_TTL_DEFAULT)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro interno ao processar estatísticas")

@app.get("/api/despesas-por-uf", response_model=DespesasPorUF)
async def despesas_por_uf(background_tasks: BackgroundTasks):
    # Retorna distribuição de despesas por UF (para gráfico)
    cache_key = "despesas_por_uf"
    cached = cache_manager.get(cache_key)
    background_tasks.add_task(cache_manager.cleanup_expired)

    if cached:
        return cached
    
    try:
        result = estatisticas_service.despesas_por_uf()
        cache_manager.set(cache_key, result, ttl=CACHE_TTL_DEFAULT)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Erro interno ao processar despesas por UF")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

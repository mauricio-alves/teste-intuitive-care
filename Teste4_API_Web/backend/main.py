import os
import uvicorn
import logging
from typing import Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query, Path, BackgroundTasks 
from fastapi.middleware.cors import CORSMiddleware

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

# Configuração de Logs básica
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CACHE_TTL_DEFAULT = 300

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eventos de startup/shutdown
    logger.info("🚀 API iniciada com sucesso!")
    logger.info("📊 Conectando ao banco de dados...")
    try:
        conn = get_db_connection()
        conn.close()
        logger.info("✅ Banco de dados conectado")
    except Exception as e:
        logger.error(f"❌ Erro ao conectar ao banco: {e}", exc_info=True)
        raise RuntimeError("Não foi possível conectar ao banco de dados")
    
    yield
    logger.info("👋 API desligada")

    try:
        from app.database import close_db_pool
        close_db_pool()
        logger.info("✅ Pool de conexões encerrado com sucesso")
    except Exception as e:
        logger.error(f"⚠️ Erro ao fechar o pool: {e}", exc_info=True)

# Inicialização do App FastAPI
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

# Raiz da API
@app.get("/")
def root():
    return {
        "message": "ANS Operadoras API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# Lista operadoras com paginação e busca
@app.get("/api/operadoras", response_model=OperadoraListResponse)
def listar_operadoras(
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(10, ge=1, le=100, description="Itens por página"),
    busca: Optional[str] = Query(
        None, 
        max_length=100,
        description="Busca por razão social ou CNPJ (máx. 100 caracteres)"
    )
):
    try:
        return operadora_service.listar_operadoras(
            page=page,
            limit=limit,
            busca=busca
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao listar operadoras: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar lista de operadoras")

# Retorna detalhes de uma operadora específica
@app.get("/api/operadoras/{cnpj}", response_model=OperadoraDetailResponse)
def detalhe_operadora(
    cnpj: str = Path(..., pattern=r"^\d{14}$", description="CNPJ da operadora. A validação é estritamente de formato (14 dígitos numéricos).")
):
    try:
        operadora = operadora_service.buscar_por_cnpj(cnpj)
        if not operadora:
            raise HTTPException(status_code=404, detail="Operadora não encontrada")
        return operadora
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao buscar detalhes da operadora {cnpj}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar detalhes da operadora")

# Retorna histórico de despesas de uma operadora
@app.get("/api/operadoras/{cnpj}/despesas", response_model=DespesasHistoricoResponse)
def historico_despesas(
    cnpj: str = Path(..., pattern=r"^\d{14}$", description="CNPJ da operadora. A validação é estritamente de formato (14 dígitos numéricos).")
):
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
        logger.error(f"❌ Erro ao buscar histórico de despesas da operadora {cnpj}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar histórico")

# Retorna estatísticas agregadas
@app.get("/api/estatisticas", response_model=EstatisticasResponse)
def estatisticas(background_tasks: BackgroundTasks):
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
        logger.error(f"❌ Erro ao calcular estatísticas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar estatísticas")

# Retorna distribuição de despesas por UF (para gráfico)
@app.get("/api/despesas-por-uf", response_model=DespesasPorUF)
def despesas_por_uf(background_tasks: BackgroundTasks):
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
        logger.error(f"❌ Erro ao calcular despesas por UF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erro interno ao processar despesas por UF")

if __name__ == "__main__":
    is_dev = os.getenv("DEBUG", "false").lower() == "true"
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=is_dev
    )

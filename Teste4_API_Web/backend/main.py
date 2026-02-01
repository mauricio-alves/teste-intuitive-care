from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn

from app.database import get_db_connection
from app.models import (
    OperadoraDetailResponse,
    DespesasHistoricoResponse,
    EstatisticasResponse,
    OperadoraListResponse
)
from app.services import OperadoraService, EstatisticasService
from app.cache import cache_manager

app = FastAPI(
    title="ANS Operadoras API",
    description="API para consulta de dados de operadoras de planos de saúde",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serviços
operadora_service = OperadoraService()
estatisticas_service = EstatisticasService()

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
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/operadoras/{cnpj}", response_model=OperadoraDetailResponse)
async def detalhe_operadora(cnpj: str):
    # Retorna detalhes de uma operadora específica
    try:
        operadora = operadora_service.buscar_por_cnpj(cnpj)
        if not operadora:
            raise HTTPException(status_code=404, detail="Operadora não encontrada")
        return operadora
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/operadoras/{cnpj}/despesas", response_model=DespesasHistoricoResponse)
async def historico_despesas(cnpj: str):
    # Retorna histórico de despesas de uma operadora
    try:
        historico = operadora_service.buscar_historico_despesas(cnpj)
        if historico['total_registros'] == 0:
            raise HTTPException(status_code=404, detail="Nenhuma despesa encontrada")
        return historico
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/estatisticas", response_model=EstatisticasResponse)
async def estatisticas():
    # Retorna estatísticas agregadas
    cache_key = "estatisticas_gerais"
    cached = cache_manager.get(cache_key)

    if cached:
        return cached
    
    try:
        stats = estatisticas_service.calcular_estatisticas()
        cache_manager.set(cache_key, stats, ttl=300)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/despesas-por-uf")
async def despesas_por_uf():
    # Retorna distribuição de despesas por UF (para gráfico)
    cache_key = "despesas_por_uf"
    cached = cache_manager.get(cache_key)

    if cached:
        return cached
    
    try:
        result = estatisticas_service.despesas_por_uf()
        cache_manager.set(cache_key, result, ttl=300)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    # Inicialização da API
    print("🚀 API iniciada com sucesso!")
    print("📊 Conectando ao banco de dados...")
    
    try:
        conn = get_db_connection()
        conn.close()
        print("✅ Banco de dados conectado")
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    # Finalização da API
    print("👋 API desligada")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

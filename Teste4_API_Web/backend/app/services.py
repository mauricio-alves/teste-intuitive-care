from typing import Optional, Dict, Any
from app.database import execute_query, execute_query_with_count
from app.models import (
    OperadoraListResponse,
    PaginationMeta,
    OperadoraListItem,
    OperadoraDetailResponse,
    DespesaItem,
    OperadoraBase,
    EstatisticasResponse
)
import math

class OperadoraService:
    # Serviço para operações com operadoras

    def listar_operadoras(
        self,
        page: int = 1,
        limit: int = 10,
        busca: Optional[str] = None
    ) -> OperadoraListResponse:
        # Lista operadoras com paginação offset-based    
        offset = (page - 1) * limit
        
        base_query = """
            SELECT 
                o.id,
                o.registro_ans,
                o.cnpj,
                o.razao_social,
                o.modalidade,
                o.uf,
                COALESCE(SUM(dc.valor_despesas), 0) as total_despesas
            FROM operadoras o
            LEFT JOIN despesas_consolidadas dc ON o.id = dc.operadora_id
        """
        
        where_clause = ""
        params = []
        
        if busca:
            where_clause = " WHERE o.razao_social ILIKE %s OR o.cnpj LIKE %s"
            search_term = f"%{busca}%"
            params = [search_term, search_term]
        
        query = base_query + where_clause + """
            GROUP BY o.id
            ORDER BY o.razao_social
            LIMIT %s OFFSET %s
        """
        query_params = params + [limit, offset]
        
        count_query = f"""
            SELECT COUNT(DISTINCT o.id) as count
            FROM operadoras o
            {where_clause}
        """
        
        results, total = execute_query_with_count(
            query,
            count_query,
            tuple(query_params) if query_params else None
        )
        
        operadoras = [OperadoraListItem(**row) for row in results]
        
        total_pages = math.ceil(total / limit) if total > 0 else 0
        meta = PaginationMeta(
            page=page,
            limit=limit,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1
        )
        
        return OperadoraListResponse(data=operadoras, meta=meta)
    
    def buscar_por_cnpj(self, cnpj: str) -> Optional[OperadoraDetailResponse]:
        # Busca operadora por CNPJ
        query = """
            SELECT 
                o.*,
                COUNT(dc.id) as total_registros,
                COALESCE(SUM(dc.valor_despesas), 0) as total_despesas,
                COALESCE(AVG(dc.valor_despesas), 0) as media_despesas
            FROM operadoras o
            LEFT JOIN despesas_consolidadas dc ON o.id = dc.operadora_id
            WHERE o.cnpj = %s
            GROUP BY o.id
        """
        
        result = execute_query(query, (cnpj,), fetch_one=True)
        
        if result:
            return OperadoraDetailResponse(**result)
        return None
    
    def buscar_historico_despesas(self, cnpj: str) -> Dict[str, Any]:
        # Busca histórico de despesas de uma operadora
        operadora_query = """
            SELECT id, registro_ans, cnpj, razao_social, modalidade, uf
            FROM operadoras
            WHERE cnpj = %s
        """
        operadora = execute_query(operadora_query, (cnpj,), fetch_one=True)
        
        if not operadora:
            return {
                'operadora': None,
                'despesas': [],
                'total_registros': 0,
                'soma_total': 0,
                'media': 0
            }
        
        despesas_query = """
            SELECT 
                ano,
                trimestre,
                SUM(valor_despesas) as valor_despesas,
                CONCAT(ano, '-T', trimestre) as periodo
            FROM despesas_consolidadas
            WHERE operadora_id = %s
            GROUP BY ano, trimestre
            ORDER BY ano, trimestre
        """
        despesas = execute_query(despesas_query, (operadora['id'],))
        
        soma_total = sum(d['valor_despesas'] for d in despesas)
        total_registros = len(despesas)
        media = soma_total / total_registros if total_registros > 0 else 0
        
        return {
            'operadora': OperadoraBase(**operadora),
            'despesas': [DespesaItem(**d) for d in despesas],
            'total_registros': total_registros,
            'soma_total': float(soma_total),
            'media': float(media)
        }


class EstatisticasService:
    # Serviço para estatísticas agregadas
    
    def calcular_estatisticas(self) -> EstatisticasResponse:
        # Estatísticas gerais das despesas consolidadas
        stats_query = """
            SELECT 
                COALESCE(SUM(valor_despesas), 0) as total_despesas,
                COALESCE(AVG(valor_despesas), 0) as media_despesas,
                COUNT(DISTINCT operadora_id) as total_operadoras,
                COUNT(*) as total_registros,
                MIN(ano) as ano_min,
                MAX(ano) as ano_max,
                MIN(trimestre) as trimestre_min,
                MAX(trimestre) as trimestre_max
            FROM despesas_consolidadas
        """
        stats = execute_query(stats_query, fetch_one=True)
        
        top5_query = """
            SELECT 
                o.razao_social,
                o.uf,
                SUM(dc.valor_despesas) as total_despesas
            FROM operadoras o
            INNER JOIN despesas_consolidadas dc ON o.id = dc.operadora_id
            GROUP BY o.id, o.razao_social, o.uf
            ORDER BY total_despesas DESC
            LIMIT 5
        """
        top5 = execute_query(top5_query)
        
        return EstatisticasResponse(
            total_despesas=float(stats['total_despesas']),
            media_despesas=float(stats['media_despesas']),
            total_operadoras=stats['total_operadoras'],
            total_registros=stats['total_registros'],
            top_5_operadoras=[dict(row) for row in top5],
            periodo_analise={
                'ano_inicial': stats['ano_min'],
                'ano_final': stats['ano_max'],
                'trimestre_inicial': stats['trimestre_min'],
                'trimestre_final': stats['trimestre_max']
            }
        )
    
    def despesas_por_uf(self) -> Dict[str, Any]:
        # Retorna despesas agregadas por UF (para gráfico)
        query = """
            SELECT 
                o.uf,
                SUM(dc.valor_despesas) as total_despesas
            FROM operadoras o
            INNER JOIN despesas_consolidadas dc ON o.id = dc.operadora_id
            WHERE o.uf IS NOT NULL
            GROUP BY o.uf
            ORDER BY total_despesas DESC
            LIMIT 10
        """
        results = execute_query(query)
        
        return {
            'ufs': [row['uf'] for row in results],
            'valores': [float(row['total_despesas']) for row in results]
        }

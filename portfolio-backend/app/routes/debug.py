from fastapi import APIRouter, HTTPException
from app.agents.advanced_rag import advanced_rag
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/debug/test-rag")
async def test_rag(query: str = "TaxoCapsNet"):
    """Test RAG system"""
    try:
        results = await advanced_rag.test_vector_search(query)
        
        return {
            "status": "debug",
            "query": query,
            "results_count": len(results) if results else 0,
            "results": results
        }
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/debug/database-stats")
async def database_stats():
    """Check database stats"""
    from app.models.database import db
    
    try:
        # Get basic stats
        docs_response = db.client.table("portfolio_documents").select("id").execute()
        chunks_response = db.client.table("portfolio_chunks").select("id").execute()
        
        doc_count = len(docs_response.data)
        chunk_count = len(chunks_response.data)
        
        # Get sources
        sources = db.client.table("portfolio_documents").select("title").execute()
        source_list = [s.get("title") for s in sources.data]
        
        return {
            "status": "success",
            "documents": doc_count,
            "chunks": chunk_count,
            "sources": source_list,
            "avg_chunks_per_doc": chunk_count / doc_count if doc_count > 0 else 0
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

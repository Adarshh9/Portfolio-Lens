import logging
from typing import List
from app.models.database import db
from app.embeddings.nomic import embedding_model
from app.models.schemas import RetrievedChunk

logger = logging.getLogger(__name__)

async def retrieve_relevant_chunks(query: str, top_k: int = 5) -> List[RetrievedChunk]:
    """Retrieve relevant portfolio chunks"""
    try:
        # Generate query embedding
        query_embedding = embedding_model.embed_query(query)
        
        # Search Supabase
        results = await db.vector_search(
            query_embedding=query_embedding,
            match_threshold=0.6,
            match_count=top_k
        )
        
        chunks = []
        for result in results:
            chunk = RetrievedChunk(
                id=result.get("id", ""),
                content=result.get("content", ""),
                source=result.get("metadata", {}).get("source", ""),
                project_type=result.get("metadata", {}).get("project_type", ""),
                similarity=result.get("similarity", 0)
            )
            chunks.append(chunk)
        
        logger.info(f"Retrieved {len(chunks)} chunks for query")
        return chunks
        
    except Exception as e:
        logger.error(f"RAG retrieval error: {e}")
        return []

def format_context_for_prompt(chunks: List[RetrievedChunk]) -> str:
    """Format retrieved chunks into prompt context"""
    if not chunks:
        return "No relevant portfolio content found."
    
    context = ""
    for idx, chunk in enumerate(chunks):
        source = chunk.source or "Unknown"
        context += f"[Source {idx + 1}: {source}]\n{chunk.content}\n\n"
    
    return context

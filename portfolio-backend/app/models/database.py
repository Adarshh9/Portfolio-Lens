from supabase import create_client
from app.config import settings
import logging
from datetime import datetime
from typing import List, Dict, Optional
import uuid


logger = logging.getLogger(__name__)

class SupabaseClient:
    def __init__(self):
        self.client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY
        )
    
    async def insert_chunk(self, document_id: str, content: str, embedding: list, metadata: dict):
        """Insert chunk with embedding"""
        try:
            response = self.client.table("portfolio_chunks").insert({
                "document_id": document_id,
                "content": content,
                "embedding": embedding,
                "metadata": metadata
            }).execute()
            
            # response.data is [dict] - extract first dict
            if isinstance(response.data, list) and len(response.data) > 0:
                return response.data[0]  # Return first element
            
            logger.error(f"Chunk insert returned: {response.data}")
            return None
            
        except Exception as e:
            logger.error(f"Error inserting chunk: {e}")
            raise
    
    async def insert_document(self, title: str, source: str, project_type: str, content: str):
        """Insert document"""
        try:
            response = self.client.table("portfolio_documents").insert({
                "title": title,
                "source": source,
                "project_type": project_type,
                "content": content,
                "metadata": {"ingested_at": str(datetime.now())}
            }).execute()
            
            # DEBUG: Print what we actually got
            logger.info(f"response.data = {response.data}")
            logger.info(f"type(response.data) = {type(response.data)}")
            
            # response.data is a list of dicts
            # Check: is it a list?
            if not isinstance(response.data, list):
                logger.error(f"response.data is not list, got {type(response.data)}")
                return None
            
            # Check: does it have items?
            if len(response.data) == 0:
                logger.error(f"response.data is empty list")
                return None
            
            # Extract first dict - THIS WAS THE BUG!
            first_item = response.data[0]  # Add [0] to get first element
            logger.info(f"first_item = {first_item}")
            logger.info(f"type(first_item) = {type(first_item)}")
            
            # Check: is first item a dict?
            if not isinstance(first_item, dict):
                logger.error(f"first_item is not dict: {type(first_item)}")
                return None
            
            logger.info(f"✓ Document inserted: {first_item.get('id', 'NO_ID')}")
            return first_item
            
        except Exception as e:
            logger.error(f"Error inserting document: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def vector_search(self, query_embedding: list, match_threshold: float = 0.6, match_count: int = 5):
        """Vector similarity search using pgvector RPC"""
        try:
            response = self.client.rpc(
                "match_portfolio_chunks",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": match_threshold,
                    "match_count": match_count
                }
            ).execute()
            
            # FIX: Handle nested list [[dict]] vs [dict]
            results = response.data
            
            # If results is nested [[dict]], flatten it
            if results and isinstance(results, list) and len(results) > 0:
                if isinstance(results[0], list):
                    logger.info(f"⚠️ Flattening nested list results")
                    results = results[0]
            
            # Add source from metadata
            for item in results:
                if isinstance(item, dict) and 'metadata' in item:
                    metadata = item.get('metadata', {})
                    if isinstance(metadata, dict):
                        item['source'] = metadata.get('title', metadata.get('source', 'unknown'))
                    else:
                        item['source'] = 'unknown'
                else:
                    item['source'] = 'unknown'
            
            logger.info(f"✓ Vector search: {len(results)} chunks, sources: {[item.get('source') for item in results[:3]]}")
            
            return results if isinstance(results, list) else []
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    async def insert_message(self, session_id: str, role: str, content: str, mode: str, judge_score: dict = None):
        """Insert chat message"""
        try:
            response = self.client.table("messages").insert({
                "session_id": session_id,
                "role": role,
                "content": content,
                "mode": mode,
                "judge_score": judge_score
            }).execute()
            
            if isinstance(response.data, list) and len(response.data) > 0:
                return response.data[0]  # Return first element
            return None
            
        except Exception as e:
            logger.error(f"Error inserting message: {e}")
            raise

    async def log_query(self, query: str, mode: str, response_quality: float, sources: List[str]):
        """Log query for analytics"""
        try:
            response = self.client.table("analytics_queries").insert({
                "query": query,
                "mode": mode,
                "response_quality_score": response_quality,
                "sources": sources,
                "timestamp": datetime.now().isoformat()
            }).execute()
            
            logger.info(f"✓ Analytics logged: {query[:30]}... (quality: {response_quality:.1f})")
            return response.data
            
        except Exception as e:
            logger.error(f"Error logging analytics: {e}")
            return None

    async def get_popular_queries(self, limit: int = 10, mode: Optional[str] = None) -> List[tuple]:
        """Get most frequently asked questions"""
        try:
            query = self.client.table("analytics_queries").select("query")
            
            if mode:
                query = query.eq("mode", mode)
            
            response = query.execute()
            
            # Count occurrences
            query_counts = {}
            for item in response.data:
                q = item.get("query", "")
                if q:
                    query_counts[q] = query_counts.get(q, 0) + 1
            
            # Sort by count
            sorted_queries = sorted(query_counts.items(), key=lambda x: x[1], reverse=True)
            
            logger.info(f"Popular queries ({mode or 'all'}): {len(sorted_queries)} unique")
            return sorted_queries[:limit]
            
        except Exception as e:
            logger.error(f"Error getting popular queries: {e}")
            return []

    async def get_quality_metrics(self, hours: int = 24) -> Dict:
        """Get response quality metrics"""
        try:
            response = self.client.table("analytics_queries").select(
                "response_quality_score, mode"
            ).execute()
            
            scores = response.data
            
            if not scores:
                return {
                    "average_quality": 0,
                    "by_mode": {},
                    "total_queries": 0
                }
            
            # Calculate metrics
            total_quality = 0
            by_mode = {}
            
            for score in scores:
                quality = score.get("response_quality_score", 0)
                mode = score.get("mode", "unknown")
                
                total_quality += quality
                
                if mode not in by_mode:
                    by_mode[mode] = {"total": 0, "count": 0, "average": 0}
                
                by_mode[mode]["total"] += quality
                by_mode[mode]["count"] += 1
            
            # Calculate averages
            for mode in by_mode:
                count = by_mode[mode]["count"]
                by_mode[mode]["average"] = by_mode[mode]["total"] / count if count > 0 else 0
            
            result = {
                "average_quality": total_quality / len(scores) if scores else 0,
                "by_mode": by_mode,
                "total_queries": len(scores)
            }
            
            logger.info(f"Quality metrics: avg={result['average_quality']:.2f}/10, queries={len(scores)}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting quality metrics: {e}")
            return {"average_quality": 0, "by_mode": {}, "total_queries": 0}

    async def get_mode_distribution(self) -> Dict[str, int]:
        """Get distribution of queries by mode"""
        try:
            response = self.client.table("analytics_queries").select("mode").execute()
            
            distribution = {}
            for item in response.data:
                mode = item.get("mode", "unknown")
                distribution[mode] = distribution.get(mode, 0) + 1
            
            logger.info(f"Mode distribution: {distribution}")
            return distribution
            
        except Exception as e:
            logger.error(f"Error getting mode distribution: {e}")
            return {}

    async def get_conversation_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Get conversation history"""
        try:
            response = self.client.table("messages")\
                .select("role, content")\
                .eq("session_id", session_id)\
                .order("created_at", desc=False)\
                .limit(limit)\
                .execute()
            
            history = [
                {"role": item.get("role"), "content": item.get("content")}
                for item in response.data
            ]
            
            logger.info(f"✓ Loaded {len(history)} messages from session {session_id}")
            return history
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            return []

    async def save_message(self, session_id: str, role: str, content: str):
        """Save message to conversation history"""
        try:
            response = self.client.table("messages").insert({
                "session_id": session_id,
                "role": role,
                "content": content,
                "created_at": datetime.now().isoformat()
            }).execute()
            
            logger.info(f"✓ Saved {role} message to session {session_id}")
            return response.data
            
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None

    async def create_session(self, user_id: Optional[str] = None) -> Optional[str]:
        """Create new conversation session"""
        try:
            session_id = str(uuid.uuid4())
            
            response = self.client.table("chat_sessions").insert({
                "id": session_id,
                "user_id": user_id,
                "created_at": datetime.now().isoformat()
            }).execute()
            
            logger.info(f"✓ Created session: {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return None

# Global instance
db = SupabaseClient()
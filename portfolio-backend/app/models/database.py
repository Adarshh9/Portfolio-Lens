from supabase import create_client
from app.config import settings
import logging
from datetime import datetime

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
            
            if not isinstance(response.data, list):
                logger.warning(f"RPC response.data not list: {type(response.data)}")
                return []
            
            return response.data
            
        except Exception as e:
            logger.error(f"Error in vector search: {e}")
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

# Global instance
db = SupabaseClient()
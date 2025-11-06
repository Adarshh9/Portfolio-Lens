import logging
from typing import List
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

class NomicEmbeddings:
    """
    Free embedding model using Nomic Embed Text v1.5
    - 768 dimensions
    - No API cost
    - Runs locally
    - MIT License
    """
    
    def __init__(self):
        logger.info("Loading Nomic Embed Text model...")
        try:
            self.model = SentenceTransformer(
                "nomic-ai/nomic-embed-text-v1.5",
                trust_remote_code=True,
                device="cpu"
            )
            logger.info(f"✓ Model loaded successfully")
            logger.info(f"✓ Model type: {type(self.model)}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """
        Embed a single query
        Returns: flat list of 768 floats
        """
        try:
            # Encode returns numpy array of shape (1, 768)
            embeddings = self.model.encode([text])
            
            # embeddings is shape (1, 768)
            if isinstance(embeddings, np.ndarray):
                # Get first row (only one), convert to list
                result = embeddings[0].tolist()
            else:
                # Shouldn't happen, but handle it
                logger.error(f"Unexpected embedding type: {type(embeddings)}")
                result = list(embeddings)
            
            # Validate
            if not isinstance(result, list):
                logger.error(f"Result is {type(result)}, expected list")
                raise ValueError(f"Embedding result is {type(result)}, not list")
            
            if len(result) != 768:
                logger.error(f"Embedding has {len(result)} dimensions, expected 768")
                raise ValueError(f"Wrong embedding dimension: {len(result)}")
            
            logger.debug(f"✓ Embedding created: {len(result)} dims, type={type(result)}")
            return result
            
        except Exception as e:
            logger.error(f"Error embedding text: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Embed multiple texts
        Returns: list of embeddings (each is list of 768 floats)
        """
        try:
            embeddings = self.model.encode(texts)
            return [emb.tolist() for emb in embeddings]
        except Exception as e:
            logger.error(f"Error embedding batch: {e}")
            raise

# Global instance
embedding_model = NomicEmbeddings()

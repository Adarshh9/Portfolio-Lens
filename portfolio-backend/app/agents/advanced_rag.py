import logging
import numpy as np
from typing import List, Dict, Union
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.schemas import RetrievedChunk
from app.models.database import db
from app.embeddings.nomic import embedding_model

logger = logging.getLogger(__name__)

class AdvancedRAG:
    """Multi-level RAG with clustering and re-ranking"""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=100, stop_words='english')
    
    def _convert_to_chunks(self, results: List[Union[dict, RetrievedChunk]]) -> List[RetrievedChunk]:
        """Convert database results to RetrievedChunk objects"""
        chunks = []
        for item in results:
            if isinstance(item, RetrievedChunk):
                chunks.append(item)
            elif isinstance(item, dict):
                # Convert dict to RetrievedChunk
                chunk = RetrievedChunk(
                    id=item.get('id', ''),
                    content=item.get('content', ''),
                    source=item.get('source', 'unknown'),
                    embedding=item.get('embedding', []),
                    similarity=item.get('similarity', 0.0)
                )
                chunks.append(chunk)
            else:
                logger.warning(f"Unknown chunk type: {type(item)}")
        
        return chunks
    
    def _deduplicate_chunks(self, chunks: List[RetrievedChunk], threshold: float = 0.85) -> List[RetrievedChunk]:
        """Remove near-duplicate chunks"""
        if len(chunks) <= 1:
            return chunks
        
        try:
            texts = [chunk.content for chunk in chunks]
            tfidf_matrix = self.vectorizer.fit_transform(texts)
            similarity_matrix = cosine_similarity(tfidf_matrix)
            
            kept_indices = [0]
            
            for i in range(1, len(chunks)):
                max_similarity = max([similarity_matrix[i][j] for j in kept_indices])
                
                if max_similarity < threshold:
                    kept_indices.append(i)
            
            deduplicated = [chunks[i] for i in kept_indices]
            logger.info(f"Deduplication: {len(chunks)} → {len(deduplicated)} chunks")
            
            return deduplicated
            
        except Exception as e:
            logger.warning(f"Deduplication failed: {e}, returning all chunks")
            return chunks
    
    def _rerank_by_relevance(self, chunks: List[RetrievedChunk], query: str, top_k: int = 5) -> List[RetrievedChunk]:
        """Re-rank chunks using cross-encoder style scoring"""
        if len(chunks) <= top_k:
            return chunks
        
        try:
            # Get query embedding
            query_emb = embedding_model.embed_query(query)
            query_emb = np.array(query_emb)
            
            # Score each chunk
            scores = []
            for chunk in chunks:
                # Get chunk embedding (use stored embedding if available)
                if hasattr(chunk, 'embedding') and chunk.embedding:
                    chunk_emb = np.array(chunk.embedding)
                else:
                    # Fallback: generate embedding
                    chunk_emb = np.array(embedding_model.embed_query(chunk.content))
                
                # Ensure dimension match
                if len(chunk_emb) != len(query_emb):
                    logger.warning(f"Dimension mismatch: query={len(query_emb)}, chunk={len(chunk_emb)}")
                    continue
                
                # Cosine similarity
                similarity = np.dot(query_emb, chunk_emb) / (
                    np.linalg.norm(query_emb) * np.linalg.norm(chunk_emb) + 1e-10
                )
                
                # Boost score if query terms appear in chunk
                query_terms = set(query.lower().split())
                chunk_text = chunk.content.lower()
                term_match_score = sum(
                    1 for term in query_terms if term in chunk_text
                ) / len(query_terms) if query_terms else 0
                
                # Combined score
                combined_score = 0.7 * similarity + 0.3 * term_match_score
                scores.append((chunk, combined_score))
            
            # Sort by score
            sorted_chunks = sorted(scores, key=lambda x: x[1], reverse=True)
            reranked = [chunk for chunk, score in sorted_chunks[:top_k]]
            
            logger.info(f"Re-ranked {len(chunks)} chunks, keeping top {top_k}")
            return reranked
            
        except Exception as e:
            logger.warning(f"Re-ranking failed: {e}, returning original chunks")
            return chunks[:top_k]
    
    def _cluster_by_project(self, chunks: List[RetrievedChunk]) -> Dict[str, List[RetrievedChunk]]:
        """Group chunks by source project"""
        clusters = {}
        for chunk in chunks:
            source = chunk.source or "unknown"
            if source not in clusters:
                clusters[source] = []
            clusters[source].append(chunk)
        
        return clusters
    
    def _select_diverse_chunks(self, clusters: Dict[str, List[RetrievedChunk]], target_count: int = 5) -> List[RetrievedChunk]:
        """Select chunks maintaining diversity across projects"""
        if not clusters:
            return []
        
        selected = []
        chunk_per_project = max(1, target_count // len(clusters))
        
        for source, source_chunks in sorted(clusters.items()):
            selected.extend(source_chunks[:chunk_per_project])
        
        # Fill remaining quota with highest similarity chunks
        if len(selected) < target_count:
            remaining = target_count - len(selected)
            for source, source_chunks in clusters.items():
                additional = source_chunks[chunk_per_project:chunk_per_project + remaining]
                selected.extend(additional)
                remaining -= len(additional)
                if remaining <= 0:
                    break
        
        return selected[:target_count]
    
    async def test_vector_search(self, query: str):
        """Debug vector search"""
        logger.info(f"\n=== TESTING VECTOR SEARCH ===")
        logger.info(f"Query: {query}")
        
        try:
            # Generate embedding
            embedding = embedding_model.embed_query(query)
            logger.info(f"Embedding generated: {len(embedding)} dimensions")
            logger.info(f"First 5 values: {embedding[:5]}")
            
            # Raw database query
            logger.info(f"\nCalling vector_search...")
            results = await db.vector_search(
                query_embedding=embedding,
                match_threshold=0.5,  # Lower threshold for testing
                match_count=10
            )
            
            logger.info(f"Results returned: {len(results)} chunks")
            
            if results:
                logger.info(f"First result type: {type(results)}")
                logger.info(f"First result keys: {results.keys() if isinstance(results, dict) else 'N/A'}")
                logger.info(f"First result: {results}")
            else:
                logger.warning("NO RESULTS RETURNED!")
            
            return results
            
        except Exception as e:
            logger.error(f"Test failed: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def retrieve_advanced(self, query: str, top_k: int = 5) -> List[RetrievedChunk]:
        """Multi-level RAG retrieval"""
        logger.info(f"🔍 Advanced RAG retrieval for: '{query[:50]}...'")
        
        try:
            # Level 1: Initial retrieval (get more than needed)
            logger.info("  Level 1: Initial retrieval...")
            initial_results = await db.vector_search(
                query_embedding=embedding_model.embed_query(query),
                match_threshold=0.6,
                match_count=top_k * 3  # Get 3x what we need
            )
            
            if not initial_results:
                logger.warning("  No chunks found in initial retrieval")
                return []
            
            # Convert to RetrievedChunk objects
            initial_chunks = self._convert_to_chunks(initial_results)
            logger.info(f"  ✓ Retrieved {len(initial_chunks)} candidates")
            
            if not initial_chunks:
                logger.warning("  Failed to convert results to chunks")
                return []
            
            # Level 2: Deduplication
            logger.info("  Level 2: Deduplication...")
            deduplicated = self._deduplicate_chunks(initial_chunks, threshold=0.80)
            
            # Level 3: Clustering by project
            logger.info("  Level 3: Clustering by project...")
            clusters = self._cluster_by_project(deduplicated)
            logger.info(f"  ✓ Found {len(clusters)} projects: {list(clusters.keys())}")
            
            # Level 4: Diverse selection
            logger.info("  Level 4: Selecting diverse chunks...")
            diverse_chunks = self._select_diverse_chunks(clusters, target_count=top_k * 2)
            
            # Level 5: Re-ranking by relevance
            logger.info("  Level 5: Re-ranking by relevance...")
            final_chunks = self._rerank_by_relevance(diverse_chunks, query, top_k=top_k)
            
            logger.info(f"  ✓ Final: {len(final_chunks)} chunks from {len(set(c.source for c in final_chunks))} projects")
            
            return final_chunks
            
        except Exception as e:
            logger.error(f"Advanced RAG failed: {e}")
            import traceback
            traceback.print_exc()
            return []

# Global instance
advanced_rag = AdvancedRAG()
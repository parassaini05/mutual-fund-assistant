"""
retrieval/retriever.py — Phase 3: Vector similarity search.

Loads the FAISS index and metadata.
Takes a user query, embeds it via the embedder, and retrieves the top-K chunks.
"""

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import TOP_K, SIMILARITY_THRESHOLD
from ingestion.embedder import embed_query
from ingestion.vector_store import load_index

logger = logging.getLogger("retriever")

class Retriever:
    def __init__(self):
        logger.info("Initializing Retriever...")
        self.index, self.metadata = load_index()
        logger.info(f"Retriever initialized. Corpus size: {self.index.ntotal}")

    def retrieve(self, query: str, top_k: int = TOP_K, threshold: float = SIMILARITY_THRESHOLD) -> list[dict]:
        """
        Embeds the query and fetches the top_k most similar chunks.
        Only returns chunks with a similarity score >= threshold.
        """
        logger.info(f"Retrieving top {top_k} chunks for query: '{query}'")
        
        # 1. Embed query
        q_emb = embed_query(query)
        
        # 2. Search FAISS index (inner product = cosine similarity for L2-normalized vectors)
        distances, indices = self.index.search(q_emb, top_k)
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS returns -1 if there are fewer vectors than k
                continue
                
            score = float(dist)
            if score < threshold:
                logger.debug(f"  -> Dropped chunk {idx} (score {score:.3f} < threshold {threshold})")
                continue
                
            chunk_meta = self.metadata[idx]
            # Attach score to metadata
            result_dict = dict(chunk_meta)
            result_dict["similarity_score"] = score
            results.append(result_dict)
            
        logger.info(f"  -> Retrieved {len(results)} chunks above threshold {threshold}")
        return results

# Singleton pattern for the retriever instance
_retriever_instance = None

def get_retriever() -> Retriever:
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = Retriever()
    return _retriever_instance

def retrieve_chunks(query: str, top_k: int = TOP_K) -> list[dict]:
    """Convenience function to get the global retriever and search."""
    retriever = get_retriever()
    return retriever.retrieve(query, top_k=top_k)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ret = get_retriever()
    res = ret.retrieve("What is the expense ratio of ICICI Prudential?")
    for i, r in enumerate(res):
        print(f"\n--- Result {i+1} (Score: {r['similarity_score']:.3f}) ---")
        print(f"Fund: {r['fund_name']}")
        print(f"Text Snippet: {r['text'][:200]}...")

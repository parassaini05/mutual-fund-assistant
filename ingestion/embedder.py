"""
ingestion/embedder.py — Phase 2.6: Chunk embedding using BAAI/bge-small-en-v1.5.

Loads the BGE embedding model via FlagEmbedding and produces L2-normalised
float32 embeddings for chunks.

Design decisions:
  - Embeddings are L2-normalised so that inner-product similarity equals cosine
    similarity.
  - Batched inference prevents OOM on large corpora.
"""

import logging
import sys
import os

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import BGE_MODEL_NAME

# If chunker.py was wiped, we fallback to dict access if Chunk isn't available
try:
    from ingestion.chunker import Chunk
except ImportError:
    class Chunk:
        def __init__(self, text, **kwargs):
            self.text = text
            for k, v in kwargs.items():
                setattr(self, k, v)

logger = logging.getLogger("embedder")

# ── Constants ─────────────────────────────────────────────────────────────────

EMBED_BATCH_SIZE: int = 32          # chunks per forward pass
BGE_PASSAGE_PREFIX: str = ""        # BGE-base does not require passage prefix
EMBEDDING_DIM: int = 384            # bge-small-en-v1.5 output dimension


# ── Model singleton ───────────────────────────────────────────────────────────

_model = None   # lazy-loaded on first call


def _load_model():
    """
    Load and cache the FlagEmbedding model (singleton pattern).
    """
    global _model
    if _model is not None:
        return _model

    logger.info(f"Loading BGE model: {BGE_MODEL_NAME} (this may take a moment...)")
    try:
        from FlagEmbedding import FlagModel
        _model = FlagModel(
            BGE_MODEL_NAME,
            query_instruction_for_retrieval="Represent this sentence for searching relevant passages:",
            use_fp16=False,     # keep float32 for accuracy; set True for GPU speed-up
        )
        logger.info(f"  [OK] Model loaded: {BGE_MODEL_NAME}")
        return _model

    except Exception as e:
        logger.error(
            f"Failed to load BGE model '{BGE_MODEL_NAME}'. "
            f"Ensure FlagEmbedding and torch are installed: {e}"
        )
        raise


# ── Public API ────────────────────────────────────────────────────────────────

def embed_chunks(chunks) -> np.ndarray:
    """
    Embed a list of Chunk objects into a float32 numpy matrix.

    Each row corresponds to one chunk; rows are in the same order as the
    input list. Embeddings are L2-normalised (unit vectors).

    Args:
        chunks: List of Chunk dataclass instances (or dicts).

    Returns:
        np.ndarray of shape (len(chunks), EMBEDDING_DIM), dtype float32.
        Returns empty array of shape (0, EMBEDDING_DIM) if chunks is empty.
    """
    if not chunks:
        logger.warning("embed_chunks called with empty chunk list - returning empty array.")
        return np.empty((0, EMBEDDING_DIM), dtype=np.float32)

    model = _load_model()

    # Handle both dataclass and dict (in case chunker is missing)
    texts = [getattr(c, "text", c.get("text", "")) if isinstance(c, dict) else c.text for c in chunks]
    total = len(texts)
    logger.info(f"Embedding {total} chunks in batches of {EMBED_BATCH_SIZE}...")

    all_embeddings: list[np.ndarray] = []

    for batch_start in range(0, total, EMBED_BATCH_SIZE):
        batch = texts[batch_start: batch_start + EMBED_BATCH_SIZE]
        batch_num = batch_start // EMBED_BATCH_SIZE + 1
        total_batches = (total + EMBED_BATCH_SIZE - 1) // EMBED_BATCH_SIZE

        logger.info(f"  Batch {batch_num}/{total_batches} ({len(batch)} chunks)...")

        embeddings = model.encode(batch)                    # shape: (B, DIM)
        embeddings = np.array(embeddings, dtype=np.float32)

        # Ensure L2 normalisation
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)           # avoid divide-by-zero
        embeddings = embeddings / norms

        all_embeddings.append(embeddings)

    result = np.vstack(all_embeddings)                      # shape: (N, DIM)
    logger.info(f"  [OK] Embedding complete - matrix shape: {result.shape}")
    return result


def embed_query(query: str) -> np.ndarray:
    """
    Embed a single query string using the BGE query instruction prefix.

    Args:
        query: Raw user query string.

    Returns:
        np.ndarray of shape (1, EMBEDDING_DIM), dtype float32, L2-normalised.
    """
    model = _load_model()

    embedding = model.encode_queries([query])               # uses query instruction
    embedding = np.array(embedding, dtype=np.float32)

    # Re-normalise for safety
    norm = np.linalg.norm(embedding, axis=1, keepdims=True)
    norm = np.where(norm == 0, 1.0, norm)
    embedding = embedding / norm

    return embedding                                        # shape: (1, DIM)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Testing embed_query...")
    q = embed_query("What is the expense ratio?")
    print(f"Query shape: {q.shape}")

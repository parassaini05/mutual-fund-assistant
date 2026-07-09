"""
ingestion/vector_store.py — Phase 2.7: Build and persist the FAISS vector index.

Accepts embedded chunk vectors + their metadata and saves two files:
    data/faiss_index/index.faiss   — FAISS IndexFlatIP binary
    data/faiss_index/metadata.json — parallel list of chunk metadata dicts
"""

import json
import logging
import sys
import os
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    FAISS_INDEX_PATH,
    MIN_CORPUS_CHUNKS,
)

try:
    from ingestion.chunker import Chunk
except ImportError:
    class Chunk:
        def __init__(self, text, **kwargs):
            self.text = text
            for k, v in kwargs.items():
                setattr(self, k, v)

logger = logging.getLogger("vector_store")

_EMBEDDING_DIM: int = 384


# ── Build + Save ──────────────────────────────────────────────────────────────

def build_and_save_index(
    chunks: list[Chunk],
    embeddings: np.ndarray,
    index_path: str = FAISS_INDEX_PATH,
) -> dict:
    import faiss

    n_chunks = len(chunks)

    if embeddings.ndim != 2 or embeddings.shape[1] != _EMBEDDING_DIM:
        raise ValueError(
            f"Expected embeddings of shape (N, {_EMBEDDING_DIM}), "
            f"got {embeddings.shape}"
        )
    if embeddings.shape[0] != n_chunks:
        raise ValueError(
            f"Mismatch: {n_chunks} chunks but {embeddings.shape[0]} embeddings."
        )

    if n_chunks < MIN_CORPUS_CHUNKS:
        raise RuntimeError(
            f"Quality gate failed: only {n_chunks} chunks produced "
            f"(minimum required: {MIN_CORPUS_CHUNKS}). "
            f"Check scraper output - pages may be JS-rendered or blocked."
        )

    logger.info(f"Building FAISS IndexFlatIP | {n_chunks} vectors | dim={_EMBEDDING_DIM}")
    index = faiss.IndexFlatIP(_EMBEDDING_DIM)

    embeddings_c = np.ascontiguousarray(embeddings, dtype=np.float32)
    index.add(embeddings_c)
    logger.info(f"  [OK] FAISS index built - total vectors: {index.ntotal}")

    out_dir = Path(index_path)
    out_dir.mkdir(parents=True, exist_ok=True)

    index_file = out_dir / "index.faiss"
    metadata_file = out_dir / "metadata.json"

    faiss.write_index(index, str(index_file))
    logger.info(f"  [OK] FAISS index saved -> {index_file}")

    metadata = [chunk.to_metadata_dict() if hasattr(chunk, 'to_metadata_dict') else chunk for chunk in chunks]
    metadata_file.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"  [OK] Metadata saved   -> {metadata_file}")

    return {
        "index_path": str(index_file),
        "metadata_path": str(metadata_file),
        "num_chunks": n_chunks,
        "embedding_dim": _EMBEDDING_DIM,
    }


# ── Load ──────────────────────────────────────────────────────────────────────

def load_index(
    index_path: str = FAISS_INDEX_PATH,
) -> tuple:
    import faiss

    out_dir = Path(index_path)
    index_file = out_dir / "index.faiss"
    metadata_file = out_dir / "metadata.json"

    if not index_file.exists():
        raise FileNotFoundError(
            f"FAISS index not found at '{index_file}'. "
            f"Run ingestion/ingest.py first to build the index."
        )
    if not metadata_file.exists():
        raise FileNotFoundError(
            f"Metadata file not found at '{metadata_file}'. "
            f"Run ingestion/ingest.py first to build the index."
        )

    logger.info(f"Loading FAISS index from: {index_file}")
    index = faiss.read_index(str(index_file))
    logger.info(f"  [OK] FAISS index loaded - {index.ntotal} vectors, dim={index.d}")

    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    logger.info(f"  [OK] Metadata loaded  - {len(metadata)} entries")

    if index.ntotal != len(metadata):
        logger.warning(
            f"  [!] Index/metadata size mismatch: "
            f"{index.ntotal} vectors vs {len(metadata)} metadata entries. "
            f"Re-run ingestion to rebuild a consistent index."
        )

    return index, metadata


def get_index_stats(index_path: str = FAISS_INDEX_PATH) -> dict:
    out_dir = Path(index_path)
    index_file = out_dir / "index.faiss"
    metadata_file = out_dir / "metadata.json"

    if not index_file.exists() or not metadata_file.exists():
        return {"error": "Index not built yet. Run ingestion/ingest.py."}

    try:
        import faiss
        index = faiss.read_index(str(index_file))
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        return {
            "num_chunks": index.ntotal,
            "embedding_dim": index.d,
            "index_path": str(index_file),
            "metadata_path": str(metadata_file),
            "funds_covered": list({m.get("fund_name", "") for m in metadata}),
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("VECTOR STORE - Index Stats")
    stats = get_index_stats()
    for key, val in stats.items():
        print(f"  {key:<20}: {val}")

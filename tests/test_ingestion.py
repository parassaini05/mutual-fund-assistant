"""
tests/test_ingestion.py — Phase 2.9: Unit tests for the ingestion pipeline.

Tests cover:
  - scraper.py   : ScrapedPage structure, content validation
  - chunker.py   : chunk count, token ranges, metadata, deduplication
  - embedder.py  : embedding shape, dtype, normalisation
  - vector_store : build, save, load, stats
  - persist.py   : file creation, JSON validity
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pytest

# ── Path setup ────────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ingestion.chunker import Chunk, chunk_text
from ingestion.scraper import ScrapedPage, _validate_content


# ── Fixtures ──────────────────────────────────────────────────────────────────

SAMPLE_TEXT = """
HDFC Small Cap Fund Direct Growth

Expense Ratio: The expense ratio of HDFC Small Cap Fund Direct Growth is 0.77% per annum.
Exit Load: HDFC Small Cap Fund charges an exit load of 1% if units are redeemed within 1 year.
Minimum SIP Amount: The minimum SIP amount for HDFC Small Cap Fund is Rs 100 per month.
Risk Level: HDFC Small Cap Fund is classified as Very High Risk on the SEBI riskometer.
Benchmark: The benchmark index for HDFC Small Cap Fund is the Nifty Smallcap 250 TRI.
NAV: The NAV of HDFC Small Cap Fund Direct Growth is Rs 158.06 per unit.
AUM: The assets under management (AUM) of HDFC Small Cap Fund is Rs 38,809.48 Crore.
Lock-in Period: There is no lock-in period for HDFC Small Cap Fund.
""" * 25   # repeat to generate enough tokens for multiple chunks


@pytest.fixture
def sample_scraped_page():
    return ScrapedPage(
        fund_name="HDFC Small Cap Fund - Direct Growth",
        amc="HDFC",
        category="Small Cap",
        source_url="https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
        scraped_date="2026-07-09",
        raw_text=SAMPLE_TEXT,
        keyword_hits=["expense ratio", "exit load", "sip", "nav", "risk"],
        is_valid=True,
    )


@pytest.fixture
def sample_chunks(sample_scraped_page):
    return chunk_text(
        text=sample_scraped_page.raw_text,
        source_url=sample_scraped_page.source_url,
        fund_name=sample_scraped_page.fund_name,
        amc=sample_scraped_page.amc,
        category=sample_scraped_page.category,
        scraped_date=sample_scraped_page.scraped_date,
    )


# ── Scraper tests ─────────────────────────────────────────────────────────────

class TestContentValidation:
    def test_valid_content_with_all_keywords(self):
        text = "expense ratio exit load sip nav risk " * 50
        is_valid, found = _validate_content(text, "Test Fund")
        assert is_valid is True
        assert len(found) == 5

    def test_thin_content_rejected(self):
        is_valid, found = _validate_content("short", "Test Fund")
        assert is_valid is False
        assert found == []

    def test_partial_keywords_threshold(self):
        # 3 of 5 keywords -> valid (threshold is >= 3)
        text = "expense ratio exit load sip " * 100
        is_valid, found = _validate_content(text, "Test Fund")
        assert is_valid is True
        assert len(found) == 3

    def test_scraped_page_fields(self, sample_scraped_page):
        assert sample_scraped_page.fund_name == "HDFC Small Cap Fund - Direct Growth"
        assert sample_scraped_page.amc == "HDFC"
        assert sample_scraped_page.is_valid is True
        assert len(sample_scraped_page.raw_text) > 0


# ── Chunker tests ─────────────────────────────────────────────────────────────

class TestChunker:
    def test_chunks_produced(self, sample_chunks):
        assert len(sample_chunks) > 0, "Expected at least one chunk"

    def test_chunk_token_range(self, sample_chunks):
        for chunk in sample_chunks:
            assert chunk.token_count >= 20, f"Chunk too small: {chunk.token_count} tokens"
            assert chunk.token_count <= 600, f"Chunk too large: {chunk.token_count} tokens"

    def test_chunk_metadata_attached(self, sample_chunks):
        for chunk in sample_chunks:
            assert chunk.source_url.startswith("https://")
            assert chunk.fund_name == "HDFC Small Cap Fund - Direct Growth"
            assert chunk.amc == "HDFC"
            assert chunk.category == "Small Cap"
            assert chunk.scraped_date == "2026-07-09"

    def test_chunk_hashes_unique(self, sample_chunks):
        hashes = [c.chunk_hash for c in sample_chunks]
        assert len(hashes) == len(set(hashes)), "Duplicate chunk hashes found"

    def test_chunk_indices_sequential(self, sample_chunks):
        for i, chunk in enumerate(sample_chunks):
            assert chunk.chunk_index == i

    def test_empty_text_returns_no_chunks(self):
        chunks = chunk_text(
            text="",
            source_url="https://example.com",
            fund_name="Test Fund",
            amc="Test AMC",
            category="Test",
            scraped_date="2026-01-01",
        )
        assert chunks == []

    def test_metadata_dict_structure(self, sample_chunks):
        meta = sample_chunks[0].to_metadata_dict()
        required_keys = {"source_url", "fund_name", "amc", "category",
                         "scraped_date", "chunk_index", "token_count", "chunk_hash"}
        assert required_keys.issubset(meta.keys())


# ── Embedder tests ────────────────────────────────────────────────────────────

class TestEmbedder:
    """
    NOTE: These tests load the BGE model — they require FlagEmbedding + torch.
    Mark them as slow if needed: pytest -m "not slow"
    """

    @pytest.mark.slow
    def test_embedding_shape(self, sample_chunks):
        from ingestion.embedder import embed_chunks, EMBEDDING_DIM
        embeddings = embed_chunks(sample_chunks[:3])
        assert embeddings.shape == (3, EMBEDDING_DIM)

    @pytest.mark.slow
    def test_embedding_dtype(self, sample_chunks):
        from ingestion.embedder import embed_chunks
        embeddings = embed_chunks(sample_chunks[:2])
        assert embeddings.dtype == np.float32

    @pytest.mark.slow
    def test_embeddings_normalised(self, sample_chunks):
        from ingestion.embedder import embed_chunks
        embeddings = embed_chunks(sample_chunks[:2])
        for row in embeddings:
            norm = np.linalg.norm(row)
            assert abs(norm - 1.0) < 1e-4, f"Embedding not unit norm: {norm}"

    @pytest.mark.slow
    def test_query_embedding_shape(self):
        from ingestion.embedder import embed_query, EMBEDDING_DIM
        emb = embed_query("What is the expense ratio of HDFC Small Cap Fund?")
        assert emb.shape == (1, EMBEDDING_DIM)

    def test_empty_chunks_returns_empty_array(self):
        from ingestion.embedder import embed_chunks, EMBEDDING_DIM
        result = embed_chunks([])
        assert result.shape == (0, EMBEDDING_DIM)


# ── Vector store tests ────────────────────────────────────────────────────────

class TestVectorStore:
    @pytest.mark.slow
    def test_build_and_load_index(self, sample_chunks):
        from ingestion.embedder import embed_chunks
        from ingestion.vector_store import build_and_save_index, load_index
        import ingestion.vector_store
        ingestion.vector_store.MIN_CORPUS_CHUNKS = 1

        embeddings = embed_chunks(sample_chunks)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = build_and_save_index(
                chunks=sample_chunks,
                embeddings=embeddings,
                index_path=tmpdir,
            )

            assert result["num_chunks"] == len(sample_chunks)
            assert result["embedding_dim"] == 768
            assert Path(result["index_path"]).exists()
            assert Path(result["metadata_path"]).exists()

            # Load and verify
            index, metadata = load_index(index_path=tmpdir)
            assert index.ntotal == len(sample_chunks)
            assert len(metadata) == len(sample_chunks)

    @pytest.mark.slow
    def test_search_returns_relevant_result(self, sample_chunks):
        from ingestion.embedder import embed_chunks, embed_query
        from ingestion.vector_store import build_and_save_index, load_index
        import ingestion.vector_store
        ingestion.vector_store.MIN_CORPUS_CHUNKS = 1

        embeddings = embed_chunks(sample_chunks)

        with tempfile.TemporaryDirectory() as tmpdir:
            build_and_save_index(sample_chunks, embeddings, index_path=tmpdir)
            index, metadata = load_index(index_path=tmpdir)

            query_emb = embed_query("What is the expense ratio?")
            distances, indices = index.search(query_emb, k=1)

            assert indices[0][0] != -1, "Expected at least one result"
            assert distances[0][0] > 0.0, "Expected positive similarity score"


# ── Persist tests ─────────────────────────────────────────────────────────────

class TestPersist:
    def test_save_cleaned_text(self, sample_scraped_page, tmp_path):
        from ingestion import persist
        original_dir = persist.RAW_DATA_DIR
        original_root = persist._PROJECT_ROOT
        persist.RAW_DATA_DIR = tmp_path
        persist._PROJECT_ROOT = tmp_path

        path = persist.save_cleaned_text(
            fund_name=sample_scraped_page.fund_name,
            clean_text=sample_scraped_page.raw_text,
            source_url=sample_scraped_page.source_url,
            scraped_date=sample_scraped_page.scraped_date,
        )
        persist.RAW_DATA_DIR = original_dir
        persist._PROJECT_ROOT = original_root

        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert sample_scraped_page.fund_name in content

    def test_save_chunks_jsonl(self, sample_chunks, tmp_path):
        from ingestion import persist
        original_dir = persist.RAW_DATA_DIR
        original_root = persist._PROJECT_ROOT
        persist.RAW_DATA_DIR = tmp_path
        persist._PROJECT_ROOT = tmp_path

        path = persist.save_chunks(
            fund_name=sample_chunks[0].fund_name,
            chunks=sample_chunks,
        )
        persist.RAW_DATA_DIR = original_dir
        persist._PROJECT_ROOT = original_root

        assert path.exists()
        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == len(sample_chunks)

        # Validate each line is valid JSON with required keys
        for line in lines:
            record = json.loads(line)
            assert "text" in record
            assert "fund_name" in record
            assert "source_url" in record

import pytest
from retrieval.retriever import get_retriever, retrieve_chunks
from retrieval.context_builder import build_context
import numpy as np

def test_retriever_initialization():
    """Verify that the retriever successfully loads the FAISS index and metadata."""
    retriever = get_retriever()
    assert retriever.index is not None
    assert retriever.index.ntotal == 26
    assert len(retriever.metadata) == 26

def test_retrieve_chunks():
    """Verify that retrieval returns chunks for a known query."""
    results = retrieve_chunks("What is the expense ratio for ICICI Prudential?", top_k=3)
    
    assert len(results) > 0
    assert len(results) <= 3
    
    # The first result should ideally be from ICICI Prudential
    top_result = results[0]
    assert "ICICI Prudential" in top_result["fund_name"]
    assert "similarity_score" in top_result
    
def test_context_builder():
    """Verify that the context builder formats output correctly."""
    mock_chunks = [
        {
            "fund_name": "Test Fund",
            "source_url": "https://test.com",
            "text": "[Test Fund] This is a test chunk."
        }
    ]
    
    context = build_context(mock_chunks)
    assert "--- Document 1 ---" in context
    assert "Fund: Test Fund" in context
    assert "Source URL: https://test.com" in context
    assert "[Test Fund] This is a test chunk." in context

def test_context_builder_empty():
    """Verify behavior with empty retrieval results."""
    context = build_context([])
    assert context == "No relevant context found in the knowledge base."

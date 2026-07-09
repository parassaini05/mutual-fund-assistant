import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from api.main import app

client = TestClient(app)

@patch("api.pipeline.retrieve_chunks")
@patch("api.pipeline.get_generator")
def test_e2e_factual_query(mock_get_generator, mock_retrieve_chunks):
    mock_retrieve_chunks.return_value = [
        {"source_url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"}
    ]
    mock_gen_instance = MagicMock()
    mock_gen_instance.generate_response.return_value = "The expense ratio is 0.67%.\n\n*(Last updated from sources: 2026-07-09)*"
    mock_get_generator.return_value = mock_gen_instance

    response = client.post("/ask", json={"query": "What is the expense ratio of HDFC Small Cap Fund?"})
    assert response.status_code == 200
    
    data = response.json()
    assert "expense ratio is 0.67%" in data["answer"]
    assert data["source"] == "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"
    assert data["last_updated"] == "2026-07-09"

def test_e2e_advisory_refusal():
    # Advisory query should be caught by safety classifier before retrieval/LLM
    response = client.post("/ask", json={"query": "Should I invest in Bajaj Finserv Flexi Cap?"})
    assert response.status_code == 200
    data = response.json()
    
    assert "I am a factual assistant" in data["answer"]
    assert "amfiindia.com" in data["source"]
    assert data["last_updated"] is None

@patch("api.pipeline.retrieve_chunks")
@patch("api.pipeline.get_generator")
def test_e2e_pii_sanitization(mock_get_generator, mock_retrieve_chunks):
    mock_retrieve_chunks.return_value = [{"source_url": "http://example.com"}]
    mock_gen_instance = MagicMock()
    mock_gen_instance.generate_response.return_value = "The minimum SIP is Rs 100.\n\n*(Last updated from sources: 2026-07-09)*"
    mock_get_generator.return_value = mock_gen_instance

    response = client.post("/ask", json={"query": "My PAN is ABCDE1234F, what is the SIP amount?"})
    assert response.status_code == 200
    
    # Verify that retrieve_chunks was called with sanitized text
    mock_retrieve_chunks.assert_called_once()
    called_query = mock_retrieve_chunks.call_args[0][0]
    
    assert "ABCDE1234F" not in called_query
    assert "[REDACTED_PAN]" in called_query

@patch("api.pipeline.retrieve_chunks")
@patch("api.pipeline.get_generator")
def test_e2e_out_of_scope(mock_get_generator, mock_retrieve_chunks):
    # Retrieval yields no matches
    mock_retrieve_chunks.return_value = []
    
    mock_gen_instance = MagicMock()
    mock_gen_instance.generate_response.return_value = "I don't have verified information on that. Please refer to the official AMC website.\n\n*(Last updated from sources: 2026-07-09)*"
    mock_get_generator.return_value = mock_gen_instance

    response = client.post("/ask", json={"query": "What is the return of SBI Bluechip Fund?"})
    assert response.status_code == 200
    data = response.json()
    
    assert "I don't have verified information" in data["answer"]
    assert data["source"] is None

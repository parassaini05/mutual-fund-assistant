import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from api.main import app
from api.models import QueryResponse

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@patch("api.pipeline.retrieve_chunks")
@patch("api.pipeline.get_generator")
def test_ask_factual(mock_get_generator, mock_retrieve_chunks):
    # Mocking retrieval chunks
    mock_retrieve_chunks.return_value = [
        {"source_url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"}
    ]
    
    # Mocking LLM Generation
    mock_generator_instance = mock_get_generator.return_value
    mock_generator_instance.generate_response.return_value = "The expense ratio of HDFC Small Cap Fund – Direct Growth is 0.67%.\n\n*(Last updated from sources: 2024-07-01)*"
    
    response = client.post("/ask", json={"query": "What is the expense ratio of HDFC Small Cap Fund?"})
    assert response.status_code == 200
    
    data = response.json()
    assert data["answer"] == "The expense ratio of HDFC Small Cap Fund – Direct Growth is 0.67%."
    assert data["source"] == "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth"
    assert data["last_updated"] == "2024-07-01"

def test_ask_advisory():
    response = client.post("/ask", json={"query": "Should I invest in HDFC Small Cap Fund?"})
    assert response.status_code == 200
    
    data = response.json()
    assert "I am a factual assistant and cannot provide investment advice" in data["answer"]
    assert data["source"] == "https://www.amfiindia.com/investor-corner/investor-education.html"
    assert data["last_updated"] is None

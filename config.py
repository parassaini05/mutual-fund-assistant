"""
config.py — Centralised configuration for the Mutual Fund FAQ Assistant.

All constants are loaded from environment variables (via .env).
Import this module anywhere in the project to access shared settings.
"""

import os
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load variables from .env file if present
load_dotenv()

# ─────────────────────────────────────────────────────────────────
# Corpus — 5 Confirmed Groww Fund URLs (sole external data source)
# ─────────────────────────────────────────────────────────────────
FUND_URLS: list[dict] = [
    {
        "fund_name": "ICICI Prudential Large Cap Fund - Direct Growth",
        "amc": "ICICI Prudential",
        "category": "Large Cap",
        "url": "https://groww.in/mutual-funds/icici-prudential-large-cap-fund-direct-growth",
    },
    {
        "fund_name": "Kotak Emerging Equity Scheme - Direct Growth",
        "amc": "Kotak Mahindra",
        "category": "Mid Cap",
        "url": "https://groww.in/mutual-funds/kotak-emerging-equity-scheme-direct-growth",
    },
    {
        "fund_name": "HDFC Small Cap Fund - Direct Growth",
        "amc": "HDFC",
        "category": "Small Cap",
        "url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    },
    {
        "fund_name": "HSBC Midcap Fund - Direct Growth",
        "amc": "HSBC",
        "category": "Mid Cap",
        "url": "https://groww.in/mutual-funds/hsbc-midcap-fund-direct-growth",
    },
    {
        "fund_name": "Bajaj Finserv Flexi Cap Fund - Direct Growth",
        "amc": "Bajaj Finserv",
        "category": "Flexi Cap",
        "url": "https://groww.in/mutual-funds/bajaj-finserv-flexi-cap-fund-direct-growth",
    },
]

# ─────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL_NAME: str = os.getenv("GROQ_MODEL_NAME", "llama3-8b-8192")
BGE_MODEL_NAME: str = os.getenv("BGE_MODEL_NAME", "BAAI/bge-small-en-v1.5")

# ─────────────────────────────────────────────────────────────────
# Chunking
# ─────────────────────────────────────────────────────────────────
CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "300"))       # tokens per chunk
CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))  # token overlap between chunks
MIN_CHUNK_TOKENS: int = 30                                   # discard chunks below this

# ─────────────────────────────────────────────────────────────────
# Retrieval
# ─────────────────────────────────────────────────────────────────
TOP_K: int = int(os.getenv("TOP_K", "3"))
SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.4"))
MAX_CONTEXT_TOKENS: int = 1500   # cap tokens to protect Groq 12K TPM limit

# ─────────────────────────────────────────────────────────────────
# Vector Store
# ─────────────────────────────────────────────────────────────────
FAISS_INDEX_PATH: str = os.getenv("FAISS_INDEX_PATH", "data/faiss_index")
FAISS_INDEX_FILE: str = os.path.join(FAISS_INDEX_PATH, "index.faiss")
METADATA_FILE: str = os.path.join(FAISS_INDEX_PATH, "metadata.json")
MIN_CORPUS_CHUNKS: int = 15     # quality gate: reject index with fewer chunks

# ─────────────────────────────────────────────────────────────────
# API
# ─────────────────────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = int(os.getenv("API_PORT", "8000"))
MAX_QUERY_LENGTH: int = int(os.getenv("MAX_QUERY_LENGTH", "500"))
GROQ_TIMEOUT_SECONDS: int = 10

# ─────────────────────────────────────────────────────────────────
# Response Constraints (from Problem Statement)
# ─────────────────────────────────────────────────────────────────
MAX_RESPONSE_SENTENCES: int = 3

# ─────────────────────────────────────────────────────────────────
# Advisory Query — Trigger Keywords (Refusal Handler)
# ─────────────────────────────────────────────────────────────────
ADVISORY_KEYWORDS: list[str] = [
    "should i",
    "which is better",
    "which fund is best",
    "best fund",
    "recommend",
    "recommendation",
    "suggest",
    "suggestion",
    "will it grow",
    "good investment",
    "worth investing",
]

"""
retrieval/context_builder.py — Phase 3: Context string generation for LLM.

Takes a list of retrieved chunks and formats them into a structured context string
that the Groq LLM can easily read and cite.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import MAX_CONTEXT_TOKENS

def build_context(retrieved_chunks: list[dict]) -> str:
    """
    Formats retrieved chunks into a clean text block for the LLM.
    Enforces a strict token limit to protect Groq TPM budgets.
    
    Args:
        retrieved_chunks: List of chunk metadata dictionaries returned by retriever.py
        
    Returns:
        A single string containing the compiled context.
    """
    if not retrieved_chunks:
        return "No relevant context found in the knowledge base."
        
    context_blocks = []
    current_tokens = 0
    
    for idx, chunk in enumerate(retrieved_chunks, 1):
        chunk_tokens = chunk.get("token_count", 0)
        
        # Protect Groq rate limits by dropping chunks that exceed our strict token budget
        if current_tokens + chunk_tokens > MAX_CONTEXT_TOKENS:
            break
            
        fund_name = chunk.get("fund_name", "Unknown Fund")
        source_url = chunk.get("source_url", "Unknown URL")
        text = chunk.get("text", "")
        
        block = (
            f"--- Document {idx} ---\n"
            f"Fund: {fund_name}\n"
            f"Source URL: {source_url}\n"
            f"Content:\n{text}\n"
        )
        context_blocks.append(block)
        current_tokens += chunk_tokens
        
    return "\n".join(context_blocks)

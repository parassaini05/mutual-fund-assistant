import logging
import re
from typing import Tuple, Optional

from retrieval.retriever import retrieve_chunks
from retrieval.context_builder import build_context
from generation.safety import sanitize_input, classify_query, get_refusal_message
from generation.generator import get_generator

logger = logging.getLogger("api_pipeline")

def run_pipeline(user_query: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Runs the full RAG pipeline end-to-end.
    Returns: (answer, source, last_updated)
    """
    # 1. Sanitize
    safe_query = sanitize_input(user_query)
    
    # 2. Classify
    query_type = classify_query(safe_query)
    if query_type == "ADVISORY":
        # Return refusal
        return (
            get_refusal_message(),
            "https://www.amfiindia.com/investor-corner/investor-education.html",
            None
        )
        
    # 3. Retrieve Context
    chunks = retrieve_chunks(safe_query)
    context = build_context(chunks)
    
    # 4. Generate
    generator = get_generator()
    response = generator.generate_response(safe_query, context)
    
    # 5. Extract Source and Date from response
    source_url = chunks[0]["source_url"] if chunks else None
    
    # The date is appended by generator as `*(Last updated from sources: <date>)*`
    match = re.search(r'\*\(Last updated from sources: (.*?)\)\*', response)
    last_updated = match.group(1) if match else None
    
    if last_updated:
        answer_clean = re.sub(r'\n*\s*\*\(Last updated from sources: (.*?)\)\*', '', response).strip()
    else:
        answer_clean = response.strip()
        
    if "I don't have verified information" in answer_clean:
        # No valid source if we fallback
        source_url = None
        
    return (answer_clean, source_url, last_updated)

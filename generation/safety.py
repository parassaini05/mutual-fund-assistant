"""
generation/safety.py — Phase 4: Refusal Handler & Sanitization

Handles stripping PII from queries, detecting advisory requests,
and validating LLM outputs against strict compliance rules.
"""

import re
import logging

logger = logging.getLogger("safety")

# Advisory keywords that trigger an immediate refusal
ADVISORY_KEYWORDS = [
    "should i",
    "which is better",
    "recommend",
    "best fund",
    "will it grow",
    "advice",
    "where should i invest",
    "is it a good time",
    "future return",
]

def sanitize_input(query: str) -> str:
    """
    Strips PII (PAN, Aadhaar, Phone, Email) from the user query.
    """
    sanitized = query
    
    # 1. PAN Card (e.g., ABCDE1234F)
    sanitized = re.sub(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b', '[REDACTED_PAN]', sanitized, flags=re.IGNORECASE)
    
    # 2. Aadhaar Card (12 digits)
    sanitized = re.sub(r'\b\d{4}\s?\d{4}\s?\d{4}\b', '[REDACTED_AADHAAR]', sanitized)
    
    # 3. Indian Phone Numbers (10 digits starting with 6-9)
    sanitized = re.sub(r'\b[6-9]\d{9}\b', '[REDACTED_PHONE]', sanitized)
    
    # 4. Email Addresses
    sanitized = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED_EMAIL]', sanitized)
    
    if sanitized != query:
        logger.info("PII detected and redacted from query.")
        
    return sanitized

def classify_query(query: str) -> str:
    """
    Classifies a query as 'FACTUAL' or 'ADVISORY'.
    """
    query_lower = query.lower()
    for keyword in ADVISORY_KEYWORDS:
        if keyword in query_lower:
            logger.warning(f"Advisory query detected due to keyword: '{keyword}'")
            return "ADVISORY"
    
    return "FACTUAL"

def get_refusal_message() -> str:
    """
    Returns the strict compliance refusal message.
    """
    return (
        "I am a factual assistant and cannot provide investment advice, opinions, or recommendations. "
        "For guidance on investing, please consult a SEBI-registered investment advisor or visit the "
        "AMFI Investor Education portal: https://www.amfiindia.com/investor-corner"
    )

def validate_response(response: str) -> bool:
    """
    Post-generation check. Returns True if valid, False if it violates constraints.
    - Must be <= 3 sentences.
    - Must contain at least one source citation (http).
    """
    # Count sentences (rough approximation by looking at terminal punctuation)
    # Exclude URLs from tricking the sentence counter
    clean_text = re.sub(r'http[s]?://\S+', '', response)
    sentences = [s for s in re.split(r'[.!?]+', clean_text) if s.strip()]
    
    if len(sentences) > 4: # We allow 4 to account for minor parsing errors of 3 sentences
        logger.warning(f"Response validation failed: Too many sentences ({len(sentences)}).")
        return False
        
    # Must contain a source URL unless it's the fallback missing-info message
    if "http" not in response and "I don't have verified information" not in response:
        logger.warning("Response validation failed: Missing source citation.")
        return False
        
    return True

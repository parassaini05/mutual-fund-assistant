import pytest
from generation.safety import sanitize_input, classify_query, validate_response

def test_sanitize_input():
    query = "My PAN is ABCDE1234F and my phone is 9876543210. What is the NAV?"
    sanitized = sanitize_input(query)
    
    assert "ABCDE1234F" not in sanitized
    assert "[REDACTED_PAN]" in sanitized
    assert "9876543210" not in sanitized
    assert "[REDACTED_PHONE]" in sanitized
    assert "What is the NAV?" in sanitized

def test_classify_query_advisory():
    assert classify_query("Which is better HDFC or ICICI?") == "ADVISORY"
    assert classify_query("Should I invest in small cap?") == "ADVISORY"
    assert classify_query("Can you recommend a good fund?") == "ADVISORY"

def test_classify_query_factual():
    assert classify_query("What is the exit load of HSBC Midcap?") == "FACTUAL"
    assert classify_query("Tell me the expense ratio.") == "FACTUAL"

def test_validate_response_success():
    # 2 sentences, 1 URL. Should pass.
    valid_resp = "The exit load is 1%. You can find more details at https://groww.in/fund."
    assert validate_response(valid_resp) == True

def test_validate_response_no_url():
    # Missing URL. Should fail.
    invalid_resp = "The exit load is 1%. It is a small cap fund."
    assert validate_response(invalid_resp) == False

def test_validate_response_too_long():
    # Too many sentences. Should fail.
    long_resp = "This is sentence one. This is sentence two. This is sentence three. This is sentence four. This is sentence five. https://groww.in/fund"
    assert validate_response(long_resp) == False

def test_validate_response_fallback_override():
    # If the LLM uses the fallback missing-info string, it should pass without a URL.
    fallback_resp = "I don't have verified information on that. Please refer to the official AMC website."
    assert validate_response(fallback_resp) == True

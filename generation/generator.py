"""
generation/generator.py — Phase 4: Prompt Assembly & LLM Call

Wraps the Groq SDK to construct the strict prompt, inject retrieved context,
and stream the final response.
"""

import os
import logging
from datetime import datetime
from groq import Groq

from generation.safety import sanitize_input, classify_query, get_refusal_message, validate_response

logger = logging.getLogger("generator")

# Locked system prompt as per Phase 4 spec
SYSTEM_PROMPT = """You are a facts-only mutual fund FAQ assistant.
- Answer ONLY using the provided context.
- Your response must be 3 sentences or fewer.
- You must include exactly one source citation link from the provided context.
- Do NOT provide investment advice, opinions, or return predictions.
- If the context does not contain the answer, say:
  "I don't have verified information on that. Please refer to the official AMC website."
"""

class LLMGenerator:
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.model_name = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
        
        if not self.api_key:
            logger.error("GROQ_API_KEY not found in environment variables!")
            raise ValueError("GROQ_API_KEY is required to initialize the generator.")
            
        self.client = Groq(api_key=self.api_key)
        logger.info(f"LLMGenerator initialized with model: {self.model_name}")

    def generate_response(self, user_query: str, retrieved_context: str) -> str:
        """
        Takes the user query and the compiled context string, sanitizes it,
        checks for advisory intent, and calls the Groq LLM.
        """
        # 1. Sanitize Input
        safe_query = sanitize_input(user_query)
        
        # 2. Check Advisory Refusal
        query_type = classify_query(safe_query)
        if query_type == "ADVISORY":
            return get_refusal_message()
            
        # 3. Assemble Prompt
        prompt = f"Context:\n{retrieved_context}\n\nQuestion: {safe_query}"
        
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
        
        logger.info("Calling Groq LLM...")
        try:
            chat_completion = self.client.chat.completions.create(
                messages=messages,
                model=self.model_name,
                temperature=0.0, # Strict facts, no hallucination
                max_completion_tokens=150, # We only want ~3 sentences max
            )
            
            raw_response = chat_completion.choices[0].message.content
            
            # 4. Validate output
            if not validate_response(raw_response):
                logger.warning("Response failed strict validation constraints. Falling back.")
                # We could retry here, but for MVP we fallback to safe message
                return "I'm sorry, I was unable to generate a compliant response based on the available facts."
                
            # 5. Format Footer
            today = datetime.now().strftime("%d %b %Y")
            final_response = f"{raw_response}\n\n*(Last updated from sources: {today})*"
            
            return final_response
            
        except Exception as e:
            logger.error(f"Error calling Groq API: {e}")
            return "An error occurred while generating the response. Please try again later."

# Singleton instance
_generator_instance = None

def get_generator() -> LLMGenerator:
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = LLMGenerator()
    return _generator_instance

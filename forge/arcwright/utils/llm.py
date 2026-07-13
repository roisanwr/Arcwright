"""Lazy LLM client wrapper — works with any OpenAI-compatible API."""
import json
import os
import time
from .. import config as cfg


def llm_complete(prompt: str, system: str = None, max_retries: int = 2) -> str:
    """
    Call the configured LLM API with a prompt.
    
    Lazy-loads the client on first call. Supports any OpenAI-compatible
    provider: OpenAI, Anthropic, OpenRouter, local vLLM/llama.cpp, etc.
    
    Falls back gracefully if LLM is not configured.
    
    Args:
        prompt: The user/content prompt
        system: Optional system message
        max_retries: Number of retries on failure
    
    Returns:
        Response text, or empty string if LLM not available
    """
    if not cfg.USE_LLM or not cfg.LLM_API_URL:
        return ""
    
    for attempt in range(max_retries):
        try:
            return _call(prompt, system)
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            print(f"  ⚠️  LLM call failed: {e}")
            return ""


def _call(prompt: str, system: str = None) -> str:
    """Single LLM API call via openai-compatible endpoint."""
    # Lazy import — avoids dependency at module level
    from openai import OpenAI
    
    client = OpenAI(
        api_key=cfg.LLM_API_KEY or "sk-placeholder",
        base_url=cfg.LLM_API_URL,
    )
    
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    resp = client.chat.completions.create(
        model=cfg.LLM_MODEL or "gpt-4o-mini",
        messages=messages,
        temperature=0.1,
        max_tokens=2000,
    )
    
    return resp.choices[0].message.content.strip()

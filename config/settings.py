"""
Arcwright configuration — model providers, paths, agent settings.
Fully flexible: supports OpenAI, Anthropic, OpenRouter, Ollama (local), etc.

Each agent can use a different model/provider via the AGENT_MODELS config.
Set via environment variables or edit this file directly.
"""

import os
import warnings
from pathlib import Path
from typing import Optional, Any


# ── Project paths ──────────────────────────────────────────────────

PROJECT_ROOT    = Path(__file__).resolve().parent
FORGE_DIR       = PROJECT_ROOT / "forge"
CHROMA_DIR      = FORGE_DIR / "output" / "chroma_db"
CHROMA_COLLECTION = "storytelling_books"

# ── Default provider ──────────────────────────────────────────────
# Supported: "openai", "anthropic", "openrouter", "ollama", "custom"
# Each agent can override this.
DEFAULT_PROVIDER = os.environ.get("ARCWRIGHT_PROVIDER", "openai")

# ── Default model (fallback if agent doesn't specify) ──────────────
DEFAULT_MODEL = os.environ.get("ARCWRIGHT_MODEL", "gpt-4o-mini")

# ── API Keys ───────────────────────────────────────────────────────
# Set these in your environment. Only the ones you use need to be set.
OPENAI_API_KEY     = os.environ.get("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# ── Ollama (local) ────────────────────────────────────────────────
OLLAMA_BASE_URL = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL    = os.environ.get("OLLAMA_MODEL", "llama3")

# ── OpenRouter ────────────────────────────────────────────────────
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# ── Custom provider ────────────────────────────────────────────────
CUSTOM_API_BASE = os.environ.get("ARCWRIGHT_API_BASE", "")
CUSTOM_API_KEY  = os.environ.get("ARCWRIGHT_API_KEY", "")

# ── Per-agent model configuration ──────────────────────────────────
# Each agent can use a different provider, model, and temperature.
# Format: { agent_name: {"provider": str, "model": str, "temperature": float} }
# Omit fields to fall back to defaults above.

AGENT_MODELS: dict[str, dict[str, Any]] = {
    # Story Director — reasoning heavy, use best model
    "story_director": {
        "provider": "openai",
        "model": "gpt-4o",
        "temperature": 0.2,
    },
    # Story Miner — conversational, creative
    "story_miner": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.7,
    },
    # RAG Librarian — factual, low temp
    "rag_librarian": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.1,
    },
    # Deep Dive — analytical
    "deep_dive": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.4,
    },
    # Web Researcher — factual
    "web_researcher": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.2,
    },
    # Validator — precise scoring
    "validator": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.3,
    },
    # Outline Writer — structured
    "outline_writer": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.7,
    },
    # Script Writer — creative
    "script_writer": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.8,
    },
    # Script Writer's internal critic
    "script_critic": {
        "provider": "openai",
        "model": "gpt-4o-mini",
        "temperature": 0.3,
    },
}

# ── Embedding model (always local, free) ──────────────────────────
EMBEDDING_MODEL = "BAAI/bge-m3"

# ── Agent runtime config ──────────────────────────────────────────
MAX_INTERVIEW_ROUNDS = 5
MAX_DEBATE_ROUNDS    = 3
VALIDATION_PASS_SCORE = 35
MIN_STORY_FRAGMENTS  = 2


# ── Model Factory ──────────────────────────────────────────────────

def get_llm_for_agent(
    agent_name: str,
    overrides: Optional[dict] = None,
) -> Any:
    """
    Create a ChatLLM instance for the given agent.

    Supports: openai, anthropic, openrouter, ollama, custom
    Falls back to DEFAULT_PROVIDER / DEFAULT_MODEL if agent not configured.

    Args:
        agent_name: Key in AGENT_MODELS (e.g. "story_miner")
        overrides: Optional dict to override provider/model/temperature

    Returns:
        LangChain chat model instance (ChatOpenAI, ChatAnthropic, etc.)

    Examples:
        # Use defaults
        llm = get_llm_for_agent("story_miner")

        # Override to use local Ollama
        llm = get_llm_for_agent("story_miner", {"provider": "ollama"})

        # Override to use OpenRouter with specific model
        llm = get_llm_for_agent("story_director", {
            "provider": "openrouter",
            "model": "anthropic/claude-sonnet-4",
        })
    """
    config = dict(AGENT_MODELS.get(agent_name, {}))
    if overrides:
        config.update(overrides)

    provider = config.get("provider", DEFAULT_PROVIDER)
    model = config.get("model", DEFAULT_MODEL)
    temperature = config.get("temperature", 0.7)

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=config.get("api_key") or OPENAI_API_KEY or None,
        )

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            api_key=config.get("api_key") or ANTHROPIC_API_KEY or None,
        )

    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=config.get("api_key") or OPENROUTER_API_KEY or None,
            base_url=OPENROUTER_BASE_URL,
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model,
            temperature=temperature,
            base_url=config.get("base_url") or OLLAMA_BASE_URL,
        )

    elif provider == "custom":
        # Any OpenAI-compatible API (OpenAI, Groq, Together, etc.)
        from langchain_openai import ChatOpenAI
        base_url = config.get("base_url") or CUSTOM_API_BASE
        api_key = config.get("api_key") or CUSTOM_API_KEY or "sk-placeholder"
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
            base_url=base_url,
        )

    else:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Supported: openai, anthropic, openrouter, ollama, custom"
        )


# ── Validation ────────────────────────────────────────────────────

def check_config() -> list[str]:
    """Check config and return list of warnings."""
    warnings_list = []

    for agent_name, cfg in AGENT_MODELS.items():
        prov = cfg.get("provider", DEFAULT_PROVIDER)
        if prov == "openai" and not OPENAI_API_KEY:
            if agent_name in ("story_director", "validator", "outline_writer", "script_writer"):
                warnings_list.append(
                    f"Agent '{agent_name}' needs OPENAI_API_KEY but it's not set."
                )
        elif prov == "anthropic" and not ANTHROPIC_API_KEY:
            warnings_list.append(
                f"Agent '{agent_name}' needs ANTHROPIC_API_KEY but it's not set."
            )

    return warnings_list

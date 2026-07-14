"""
Arcwright configuration — per-agent model config, custom endpoints, API keys.
All secrets are loaded from environment variables (never hardcoded).

Tiap agent bisa punya provider, model, temperature, dan API key sendiri.
Supports: OpenAI, Anthropic, OpenRouter, Ollama (local), atau custom endpoint apapun.
"""
import os
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

load_dotenv()

# ── Project Paths ─────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHROMA_DIR   = PROJECT_ROOT / "forge" / "output" / "chroma_db"
SESSIONS_DB  = PROJECT_ROOT / "sessions.db"

# ── Global API Keys ───────────────────────────────────────────────────────────
# Kalau agent tidak set api_key sendiri, fallback ke ini
OPENAI_API_KEY     = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ── Default Provider & Model (fallback kalau agent tidak dikonfigurasi) ───────
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "openai")
DEFAULT_MODEL    = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")


def _safe_float(value: str, default: float) -> float:
    """Parse float dari env var dengan graceful fallback jika nilai tidak valid."""
    try:
        return float(value)
    except (TypeError, ValueError):
        import warnings
        warnings.warn(
            f"Invalid temperature value '{value}' in .env — using default {default}",
            stacklevel=2,
        )
        return default

# ── Per-Agent Model Configuration ─────────────────────────────────────────────
# Format per entry:
#   provider    : "openai" | "anthropic" | "openrouter" | "ollama" | "custom"
#   model       : nama model sesuai provider
#   temperature : kreativitas agent (0.0 = deterministik, 1.0 = sangat kreatif)
#   api_key     : (optional) override global key untuk agent ini saja
#   base_url    : (optional) custom endpoint, wajib untuk "openrouter", "ollama", "custom"
#
# Semua field optional — kalau tidak diisi, fallback ke DEFAULT_PROVIDER/DEFAULT_MODEL

AGENT_CONFIGS: dict[str, dict[str, Any]] = {

    # Story Director — otak pipeline, reasoning berat, pakai model terbaik
    "story_director": {
        "provider":    os.getenv("DIRECTOR_PROVIDER",  DEFAULT_PROVIDER),
        "model":       os.getenv("DIRECTOR_MODEL",     "gpt-4o-mini"),
        "temperature": _safe_float(os.getenv("DIRECTOR_TEMP", "0.2"), 0.2),
        "api_key":     os.getenv("DIRECTOR_API_KEY",   ""),   # override global key
        "base_url":    os.getenv("DIRECTOR_BASE_URL",  ""),   # custom endpoint
    },

    # Story Miner — percakapan empatik, butuh kreativitas tinggi
    "story_miner": {
        "provider":    os.getenv("MINER_PROVIDER",  DEFAULT_PROVIDER),
        "model":       os.getenv("MINER_MODEL",     "gpt-4o-mini"),
        "temperature": _safe_float(os.getenv("MINER_TEMP", "0.7"), 0.7),
        "api_key":     os.getenv("MINER_API_KEY",   ""),
        "base_url":    os.getenv("MINER_BASE_URL",  ""),
    },

    # RAG Librarian — factual retrieval, temp rendah
    "rag_librarian": {
        "provider":    os.getenv("RAG_PROVIDER",  DEFAULT_PROVIDER),
        "model":       os.getenv("RAG_MODEL",     "gpt-4o-mini"),
        "temperature": _safe_float(os.getenv("RAG_TEMP", "0.1"), 0.1),
        "api_key":     os.getenv("RAG_API_KEY",   ""),
        "base_url":    os.getenv("RAG_BASE_URL",  ""),
    },

    # Web Researcher — factual, pakai tool
    "web_researcher": {
        "provider":    os.getenv("WEB_PROVIDER",  DEFAULT_PROVIDER),
        "model":       os.getenv("WEB_MODEL",     "gpt-4o-mini"),
        "temperature": _safe_float(os.getenv("WEB_TEMP", "0.2"), 0.2),
        "api_key":     os.getenv("WEB_API_KEY",   ""),
        "base_url":    os.getenv("WEB_BASE_URL",  ""),
    },

    # Deep Dive — analitis, 5 perspektif
    "deep_dive": {
        "provider":    os.getenv("DEEPDIVE_PROVIDER",  DEFAULT_PROVIDER),
        "model":       os.getenv("DEEPDIVE_MODEL",     "gpt-4o-mini"),
        "temperature": _safe_float(os.getenv("DEEPDIVE_TEMP", "0.4"), 0.4),
        "api_key":     os.getenv("DEEPDIVE_API_KEY",   ""),
        "base_url":    os.getenv("DEEPDIVE_BASE_URL",  ""),
    },

    # Validator — scoring presisi, temp rendah
    "validator": {
        "provider":    os.getenv("VALIDATOR_PROVIDER",  DEFAULT_PROVIDER),
        "model":       os.getenv("VALIDATOR_MODEL",     "gpt-4o-mini"),
        "temperature": _safe_float(os.getenv("VALIDATOR_TEMP", "0.2"), 0.2),
        "api_key":     os.getenv("VALIDATOR_API_KEY",   ""),
        "base_url":    os.getenv("VALIDATOR_BASE_URL",  ""),
    },

    # Outline Writer — synthesis kreatif
    "outline_writer": {
        "provider":    os.getenv("OUTLINE_PROVIDER",  DEFAULT_PROVIDER),
        "model":       os.getenv("OUTLINE_MODEL",     "gpt-4o-mini"),
        "temperature": _safe_float(os.getenv("OUTLINE_TEMP", "0.7"), 0.7),
        "api_key":     os.getenv("OUTLINE_API_KEY",   ""),
        "base_url":    os.getenv("OUTLINE_BASE_URL",  ""),
    },

    # Script Writer — paling kreatif, butuh model terbaik
    "script_writer": {
        "provider":    os.getenv("SCRIPT_PROVIDER",  DEFAULT_PROVIDER),
        "model":       os.getenv("SCRIPT_MODEL",     "gpt-4o-mini"),
        "temperature": _safe_float(os.getenv("SCRIPT_TEMP", "0.8"), 0.8),
        "api_key":     os.getenv("SCRIPT_API_KEY",   ""),
        "base_url":    os.getenv("SCRIPT_BASE_URL",  ""),
    },
}

# ── Provider Base URLs ────────────────────────────────────────────────────────
PROVIDER_BASE_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama":     os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    "custom":     os.getenv("CUSTOM_API_BASE_URL", ""),
}

# ── RAG ───────────────────────────────────────────────────────────────────────
CHROMA_COLLECTION = "storytelling_books"
EMBEDDING_MODEL   = "BAAI/bge-m3"  # Must match forge/arcwright/config.py
RAG_K             = 5
RAG_FETCH_K       = 20

# ── Web Search ────────────────────────────────────────────────────────────────
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# ── LangSmith Observability (optional) ────────────────────────────────────────
LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false")
LANGCHAIN_API_KEY    = os.getenv("LANGCHAIN_API_KEY", "")
LANGCHAIN_PROJECT    = os.getenv("LANGCHAIN_PROJECT", "arcwright")

# ── Pipeline Tuning ───────────────────────────────────────────────────────────
MIN_STORY_FRAGMENTS    = 2
VALIDATOR_PASS_THRESHOLD = 35
MAX_DEBATE_ROUNDS      = 3
SCRIPT_SELF_REFINE_ROUNDS = 1

# Apply LangSmith env vars if tracing enabled
if LANGCHAIN_TRACING_V2 == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"]    = LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"]    = LANGCHAIN_PROJECT


# ── Startup Validation ────────────────────────────────────────────────────────

def validate_config(raise_on_error: bool = True) -> list[str]:
    """
    Validasi config sebelum pipeline dijalankan.
    Cek: API key, ChromaDB path, dan dependency kritis.

    Args:
        raise_on_error: Jika True, raise ValueError jika ada error kritis.

    Returns:
        List of warning strings (non-fatal issues).
    """
    errors: list[str] = []
    warnings_list: list[str] = []

    # Cek API key berdasarkan default provider
    if DEFAULT_PROVIDER == "openai" and not OPENAI_API_KEY:
        errors.append(
            "OPENAI_API_KEY tidak ditemukan di .env!\n"
            "  Isi OPENAI_API_KEY=sk-... di file .env\n"
            "  Atau ganti DEFAULT_PROVIDER=openrouter/ollama/anthropic"
        )
    elif DEFAULT_PROVIDER == "anthropic" and not ANTHROPIC_API_KEY:
        errors.append("ANTHROPIC_API_KEY tidak ditemukan di .env!")
    elif DEFAULT_PROVIDER == "openrouter" and not OPENROUTER_API_KEY:
        errors.append("OPENROUTER_API_KEY tidak ditemukan di .env!")

    # Cek ChromaDB path
    if not CHROMA_DIR.exists():
        warnings_list.append(
            f"ChromaDB directory tidak ditemukan: {CHROMA_DIR}\n"
            "  RAG Librarian akan gagal saat query. Jalankan forge pipeline dulu."
        )

    # Cek Tavily (non-fatal — web researcher akan skip gracefully)
    if not TAVILY_API_KEY:
        warnings_list.append(
            "TAVILY_API_KEY tidak diset — Web Researcher akan di-skip otomatis."
        )

    # Print warnings
    for w in warnings_list:
        print(f"  ⚠️  [CONFIG WARNING] {w}")

    # Handle errors
    if errors:
        error_msg = "\n\n".join(f"  ❌ [CONFIG ERROR] {e}" for e in errors)
        if raise_on_error:
            raise ValueError(
                f"\n\nArcwright Config Error — pipeline tidak bisa dimulai:\n\n{error_msg}\n"
            )
        for e in errors:
            print(f"  ❌ [CONFIG ERROR] {e}")

    return warnings_list


# ── LLM Factory ───────────────────────────────────────────────────────────────

def get_llm_for_agent(agent_name: str):
    """
    Build a LangChain chat model for a specific agent.
    Supports: openai, anthropic, openrouter, ollama, custom.

    Args:
        agent_name: key dari AGENT_CONFIGS (e.g. "story_miner")

    Returns:
        LangChain BaseChatModel instance
    """
    cfg = dict(AGENT_CONFIGS.get(agent_name, {}))

    provider    = cfg.get("provider", DEFAULT_PROVIDER)
    model       = cfg.get("model", DEFAULT_MODEL)
    temperature = cfg.get("temperature", 0.7)

    # Per-agent key & url — fallback ke global jika kosong
    api_key  = cfg.get("api_key") or None   # "" → None
    base_url = cfg.get("base_url") or None  # "" → None

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key or OPENAI_API_KEY or None,
            base_url=base_url or None,  # None = pakai default OpenAI endpoint
        )

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model,
            temperature=temperature,
            api_key=api_key or ANTHROPIC_API_KEY or None,
        )

    elif provider == "openrouter":
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key or OPENROUTER_API_KEY or None,
            base_url=base_url or PROVIDER_BASE_URLS["openrouter"],
        )

    elif provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=model,
            temperature=temperature,
            base_url=base_url or PROVIDER_BASE_URLS["ollama"],
        )

    elif provider == "custom":
        # Endpoint apapun yang OpenAI-compatible (Groq, Together, LM Studio, vLLM, dll)
        from langchain_openai import ChatOpenAI
        custom_url = base_url or PROVIDER_BASE_URLS["custom"]
        if not custom_url:
            raise ValueError(
                f"Agent '{agent_name}' uses provider='custom' but "
                f"no base_url found. Set {agent_name.upper().replace('_','')}_BASE_URL "
                f"or CUSTOM_API_BASE_URL in .env"
            )
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            api_key=api_key or OPENAI_API_KEY or "sk-placeholder",
            base_url=custom_url,
        )

    else:
        raise ValueError(
            f"Unknown provider '{provider}' for agent '{agent_name}'. "
            f"Supported: openai, anthropic, openrouter, ollama, custom"
        )

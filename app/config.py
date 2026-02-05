import os
from dotenv import load_dotenv

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------
load_dotenv()


# --------------------------------------------------
# Helper functions
# --------------------------------------------------
def _require_env(key: str) -> str:
    """
    Fetches a required environment variable.
    Raises a clear error if missing.
    """
    value = os.getenv(key)
    if not value:
        raise ValueError(f"{key} is not set in .env")
    return value


def _optional_env(key: str) -> str | None:
    """
    Fetches an optional environment variable.
    Returns None if missing.
    """
    return os.getenv(key)


def _get_int_env(key: str, default: int) -> int:
    """
    Safely parses an integer environment variable.
    Falls back to default if invalid.
    """
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


# --------------------------------------------------
# Gemini (Primary semantic understanding LLM)
# --------------------------------------------------
# Used for:
# - Category inference
# - Topics covered
# - Content type
# - Gap identification (max 5)
#
# NOTE:
# Gemini is OPTIONAL at runtime.
# Pipeline should still run using HF if quota is exhausted.
GEMINI_API_KEY = _optional_env("GEMINI_API_KEY")
USE_GEMINI = bool(GEMINI_API_KEY)


# --------------------------------------------------
# Hugging Face (Stable fallback / primary for free tier)
# --------------------------------------------------
# Used for:
# - Zero-shot classification
# - Gap detection via QA
HF_API_TOKEN = _require_env("HF_API_TOKEN")


# --------------------------------------------------
# Google Sheets
# --------------------------------------------------
GOOGLE_SHEET_ID = _require_env("GOOGLE_SHEET_ID")


# --------------------------------------------------
# Runtime controls
# --------------------------------------------------
# IMPORTANT for rate limits & stability
MAX_ARTICLES_PER_RUN = _get_int_env("MAX_ARTICLES_PER_RUN", default=1)

# Future-proof switches (not mandatory yet)
ENABLE_GAP_ANALYSIS = True
ENABLE_SHEET_SYNC = True
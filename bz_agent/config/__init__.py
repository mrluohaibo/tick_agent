from .init_config import (
    # Reasoning LLM
    REASONING_MODEL,
    REASONING_BASE_URL,
    REASONING_API_KEY,
    # Basic LLM
    BASIC_MODEL,
    BASIC_BASE_URL,
    BASIC_API_KEY,
    # Vision-language LLM
    VL_MODEL,
    VL_BASE_URL,
    VL_API_KEY,
    # Other configurations
    LOCAL_BASIC_MODEL_PATH,
)


# Team configuration
TEAM_MEMBERS = ["url_to_markdown", "coder", "browser", "reporter"]

__all__ = [
    # Reasoning LLM
    "REASONING_MODEL",
    "REASONING_BASE_URL",
    "REASONING_API_KEY",
    # Basic LLM
    "BASIC_MODEL",
    "BASIC_BASE_URL",
    "BASIC_API_KEY",
    # Vision-language LLM
    "VL_MODEL",
    "VL_BASE_URL",
    "VL_API_KEY",
    # Other configurations
    "LOCAL_BASIC_MODEL_PATH",
    "TEAM_MEMBERS",
]

"""
Agent Providers Package
=======================
Factory functions for creating AI provider instances.
"""

import os
import logging
from typing import Optional

from .base import BaseProvider

logger = logging.getLogger("instaharvest_v2.agent.providers")

# Environment variable names for API keys
_API_KEY_ENV = {
    "openai": "OPENAI_API_KEY",
    "claude": "ANTHROPIC_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "google": "GEMINI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "groq": "GROQ_API_KEY",
    "together": "TOGETHER_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "xai": "XAI_API_KEY",
    "grok": "XAI_API_KEY",
    "ollama": None,
}


def resolve_api_key(provider: str) -> Optional[str]:
    """Get API key for a provider from environment variables."""
    env_var = _API_KEY_ENV.get(provider.lower())
    if env_var is None:
        return None
    return os.getenv(env_var)


def get_provider(provider: str, api_key: Optional[str] = None, model: Optional[str] = None) -> BaseProvider:
    """
    Create and return an AI provider instance.

    Args:
        provider: Provider name (openai, claude, gemini, deepseek, etc.)
        api_key:  API key (uses env var if not provided)
        model:    Model name (provider default if not specified)

    Returns:
        BaseProvider subclass instance

    Raises:
        ValueError: Unknown provider name
    """
    name = provider.lower()

    if name in ("openai",):
        from .openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key or "", model=model)

    if name in ("claude", "anthropic"):
        from .claude_provider import ClaudeProvider
        return ClaudeProvider(api_key=api_key or "", model=model)

    if name in ("gemini", "google"):
        from .gemini_provider import GeminiProvider
        return GeminiProvider(api_key=api_key or "", model=model)

    # OpenAI-compatible providers
    _compat_defaults = {
        "deepseek": ("https://api.deepseek.com/v1", "deepseek-chat"),
        "qwen": ("https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-turbo"),
        "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
        "together": ("https://api.together.xyz/v1", "mistralai/Mixtral-8x7B-Instruct-v0.1"),
        "mistral": ("https://api.mistral.ai/v1", "mistral-large-latest"),
        "openrouter": ("https://openrouter.ai/api/v1", "openai/gpt-4o"),
        "xai": ("https://api.x.ai/v1", "grok-beta"),
        "grok": ("https://api.x.ai/v1", "grok-beta"),
        "ollama": ("http://localhost:11434/v1", model or "llama3"),
    }

    if name in _compat_defaults:
        from .openai_compatible import OpenAICompatibleProvider
        base_url, default_model = _compat_defaults[name]
        return OpenAICompatibleProvider(
            api_key=api_key or "ollama" if name == "ollama" else api_key or "",
            base_url=base_url,
            model=model or default_model,
        )

    raise ValueError(
        f"Unknown provider '{provider}'. "
        f"Supported: openai, claude, gemini, deepseek, qwen, groq, "
        f"together, mistral, ollama, openrouter, xai"
    )


__all__ = ["get_provider", "resolve_api_key", "BaseProvider"]

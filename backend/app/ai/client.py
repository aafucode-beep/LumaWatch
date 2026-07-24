"""LLM 客户端：OpenAI 兼容接口，默认 MiniMax，可运行时切换。"""
from __future__ import annotations

from openai import OpenAI

from ..config import settings


def get_client() -> OpenAI:
    return OpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key or "not-set",
        timeout=settings.llm_timeout,
    )


def is_configured() -> bool:
    return bool(settings.llm_api_key)

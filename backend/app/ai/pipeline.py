"""AI 提取管道：抓取结果 -> 大模型 -> 校验后的结构化草稿。"""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import settings
from ..crawler import CrawlOutput
from . import prompts
from .client import get_client, is_configured


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n", "", text)
        text = re.sub(r"\n```$", "", text)
    return text.strip()


def _extract_json(text: str) -> dict:
    text = _strip_code_fence(text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 截取第一个 { 到最后一个 }
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
def _call_llm(system: str, user: str) -> str:
    client = get_client()
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content or "{}"


def _valid_urls(candidates: list[dict]) -> set[str]:
    return {c["url"] for c in candidates if c.get("url")}


def _fallback_draft(crawl: CrawlOutput, reason: str) -> dict:
    """未配置或调用失败时，用规则结果拼一个最小草稿供人工补全。"""
    host = urlparse(crawl.final_url).netloc
    name = host.replace("www.", "").split(".")[0].title() if host else "Unknown"
    return {
        "company": {
            "name": name,
            "name_cn": None,
            "website": crawl.final_url,
            "hq_country": None,
            "hq_city": None,
            "founded_year": None,
            "history": None,
            "philosophy": None,
            "summary": None,
        },
        "offices": [],
        "product_lines": [],
        "tags": [],
        "downloads": crawl.download_links,
        "news": crawl.news_links,
        "_ai_note": f"AI 未运行（{reason}），仅返回规则抓取结果，请人工补全。",
        "_source_url": crawl.final_url,
    }


def _sanitize(draft: dict, crawl: CrawlOutput) -> dict:
    """校验与清洗：过滤臆造的 URL，补 website，规范字段。"""
    valid_dl = _valid_urls(crawl.download_links)
    valid_news = _valid_urls(crawl.news_links)

    company = draft.get("company") or {}
    if not company.get("website"):
        company["website"] = crawl.final_url
    draft["company"] = company

    # 下载：只保留候选中真实存在的 URL；AI 未给出则回退全部候选
    ai_downloads = [d for d in (draft.get("downloads") or []) if d.get("url") in valid_dl]
    draft["downloads"] = ai_downloads if ai_downloads else crawl.download_links

    ai_news = [n for n in (draft.get("news") or []) if n.get("url") in valid_news]
    draft["news"] = ai_news if ai_news else crawl.news_links

    draft.setdefault("offices", [])
    draft.setdefault("product_lines", [])
    draft.setdefault("tags", [])
    draft["_source_url"] = crawl.final_url
    return draft


def extract(crawl: CrawlOutput) -> dict:
    """主入口：把抓取结果交给大模型，返回结构化草稿 dict。"""
    if not is_configured():
        return _fallback_draft(crawl, "未配置 LLM_API_KEY")
    if not crawl.pages:
        return _fallback_draft(crawl, "无有效页面内容")

    site_text = crawl.combined_text(settings.llm_max_input_chars)
    user = prompts.build_user_prompt(site_text, crawl.download_links, crawl.news_links)
    try:
        raw = _call_llm(prompts.SYSTEM_PROMPT, user)
        draft: dict[str, Any] = _extract_json(raw)
    except Exception as e:  # noqa: BLE001
        fb = _fallback_draft(crawl, f"AI 调用失败: {e}")
        return fb
    return _sanitize(draft, crawl)

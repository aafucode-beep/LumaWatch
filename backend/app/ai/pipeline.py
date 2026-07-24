"""AI 提取管道：抓取结果 -> 大模型 -> 校验后的结构化草稿。"""
from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit

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
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        if start == -1:
            raise
        value, _end = json.JSONDecoder().raw_decode(text[start:])
    if not isinstance(value, dict):
        raise ValueError("模型输出的 JSON 顶层必须是对象")
    return value


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=20))
def _call_llm(system: str, user: str) -> str:
    client = get_client()
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.1,
        max_tokens=12000,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content or "{}"


def _canonical_url(url: str | None) -> str:
    if not url:
        return ""
    try:
        parts = urlsplit(url.strip())
        path = parts.path.rstrip("/") or "/"
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))
    except ValueError:
        return ""


def _valid_urls(candidates: list[dict]) -> dict[str, str]:
    return {
        _canonical_url(c.get("url")): c["url"]
        for c in candidates
        if c.get("url") and _canonical_url(c.get("url"))
    }


def _fallback_draft(crawl: CrawlOutput, reason: str) -> dict:
    host = urlsplit(crawl.final_url).netloc
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
        "projects": [],
        "insights": [],
        "tags": [],
        "downloads": crawl.download_links,
        "news": [],
        "evidence": [],
        "_ai_note": f"AI 未运行（{reason}），仅返回规则抓取结果，请人工补全。",
        "_source_url": crawl.final_url,
    }


def _clean_product_lines(
    items: list[dict], page_urls: dict[str, str], limit: int = 15
) -> list[dict]:
    cleaned: list[dict] = []
    for raw in items or []:
        if not isinstance(raw, dict) or not str(raw.get("name") or "").strip():
            continue
        item = dict(raw)
        source_key = _canonical_url(item.get("source_url"))
        if source_key in page_urls:
            item["source_url"] = page_urls[source_key]
        else:
            item.pop("source_url", None)
            item.pop("source_snippet", None)
        item["children"] = _clean_product_lines(
            item.get("children") or [], page_urls, limit=5
        )
        cleaned.append(item)
    return cleaned[:limit]


def _sanitize(draft: dict, crawl: CrawlOutput) -> dict:
    """过滤幻觉 URL、伪新闻与无来源洞察，并补齐稳定字段。"""
    valid_dl = _valid_urls(crawl.download_links)
    valid_news = _valid_urls(crawl.news_links)
    page_urls = {_canonical_url(p.url): p.url for p in crawl.pages}
    page_text = {_canonical_url(p.url): " ".join(p.text.split()).lower() for p in crawl.pages}

    company = draft.get("company") or {}
    if not company.get("website"):
        company["website"] = crawl.final_url
    draft["company"] = company

    downloads = []
    for item in draft.get("downloads") or []:
        if not isinstance(item, dict):
            continue
        key = _canonical_url(item.get("url"))
        if key in valid_dl:
            item = dict(item)
            item["url"] = valid_dl[key]
            downloads.append(item)
    draft["downloads"] = downloads if downloads else crawl.download_links

    news = []
    for item in draft.get("news") or []:
        if not isinstance(item, dict) or not item.get("title"):
            continue
        if not item.get("summary") and not item.get("published_date"):
            continue
        key = _canonical_url(item.get("url"))
        if key in valid_news:
            item = dict(item)
            item["url"] = valid_news[key]
            news.append(item)
    draft["news"] = news[:8]

    projects = []
    for item in draft.get("projects") or []:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        key = _canonical_url(item.get("source_url"))
        if key in page_urls:
            item = dict(item)
            item["source_url"] = page_urls[key]
            projects.append(item)
    draft["projects"] = projects[:8]

    insights = []
    for item in draft.get("insights") or []:
        if not isinstance(item, dict) or not item.get("title") or not item.get("summary"):
            continue
        key = _canonical_url(item.get("source_url"))
        if key in page_urls:
            item = dict(item)
            item["source_url"] = page_urls[key]
            insights.append(item)
    draft["insights"] = insights[:8]

    evidence = []
    for item in draft.get("evidence") or []:
        if not isinstance(item, dict) or not item.get("field"):
            continue
        key = _canonical_url(item.get("source_url"))
        snippet = " ".join(str(item.get("snippet") or "").split())[:300]
        if key not in page_urls or not snippet:
            continue
        if snippet.lower() not in page_text.get(key, ""):
            continue
        evidence.append(
            {
                "field": str(item["field"])[:64],
                "source_url": page_urls[key],
                "snippet": snippet,
            }
        )
    draft["evidence"] = evidence[:20]

    draft["product_lines"] = _clean_product_lines(
        draft.get("product_lines") or [], page_urls
    )
    draft.setdefault("offices", [])
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
    last_error: Exception | None = None
    for attempt in range(2):
        system = prompts.SYSTEM_PROMPT
        if attempt:
            system += (
                "\n上一次输出不是完整合法 JSON。本次必须精简内容、避免重复，"
                "确保所有字符串和数组闭合，并且只输出一个完整 JSON 对象。"
            )
        try:
            raw = _call_llm(system, user)
            draft: dict[str, Any] = _extract_json(raw)
            return _sanitize(draft, crawl)
        except Exception as error:  # noqa: BLE001
            last_error = error
    return _fallback_draft(crawl, f"AI 调用失败: {last_error}")

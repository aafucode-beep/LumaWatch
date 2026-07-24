"""网页抓取：优先 httpx 静态抓取，必要时用 Playwright 渲染 JS。"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urljoin, urlparse

import httpx

from ..config import settings


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    html: str
    ok: bool = True
    error: Optional[str] = None
    links: list[str] = field(default_factory=list)


_HEADERS = {
    "User-Agent": settings.crawl_user_agent,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en,zh-CN;q=0.8",
}


async def fetch_static(url: str, client: httpx.AsyncClient) -> FetchResult:
    try:
        resp = await client.get(url, follow_redirects=True, timeout=settings.crawl_timeout)
        html = resp.text if "html" in resp.headers.get("content-type", "").lower() else ""
        return FetchResult(
            url=url,
            final_url=str(resp.url),
            status=resp.status_code,
            html=html,
            ok=resp.status_code < 400,
        )
    except Exception as e:  # noqa: BLE001
        return FetchResult(url=url, final_url=url, status=0, html="", ok=False, error=str(e))


async def fetch_rendered(urls: list[str]) -> dict[str, FetchResult]:
    """用 Playwright 批量渲染。返回 url -> FetchResult。"""
    results: dict[str, FetchResult] = {}
    try:
        from playwright.async_api import async_playwright
    except Exception as e:  # noqa: BLE001
        for u in urls:
            results[u] = FetchResult(u, u, 0, "", ok=False, error=f"playwright 不可用: {e}")
        return results

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=settings.crawl_user_agent, locale="en-US"
        )
        for u in urls:
            page = await context.new_page()
            try:
                resp = await page.goto(
                    u, wait_until="networkidle", timeout=settings.crawl_timeout * 1000
                )
                await page.wait_for_timeout(800)
                html = await page.content()
                results[u] = FetchResult(
                    url=u,
                    final_url=page.url,
                    status=resp.status if resp else 200,
                    html=html,
                    ok=True,
                )
            except Exception as e:  # noqa: BLE001
                results[u] = FetchResult(u, u, 0, "", ok=False, error=str(e))
            finally:
                await page.close()
            await asyncio.sleep(settings.crawl_delay)
        await context.close()
        await browser.close()
    return results


def same_registrable_domain(a: str, b: str) -> bool:
    """粗略判断两个 URL 是否属于同一站点（末两段域名相同）。"""
    def reg(host: str) -> str:
        parts = host.split(".")
        return ".".join(parts[-2:]) if len(parts) >= 2 else host

    return reg(urlparse(a).netloc.lower()) == reg(urlparse(b).netloc.lower())


def normalize_url(base: str, href: str) -> Optional[str]:
    if not href:
        return None
    href = href.strip()
    if href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return None
    absolute = urljoin(base, href)
    parsed = urlparse(absolute)
    if parsed.scheme not in ("http", "https"):
        return None
    # 去掉 fragment
    return absolute.split("#")[0]

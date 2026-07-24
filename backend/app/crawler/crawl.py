"""探测编排：受控抓取首页和多层高价值页面，产出结构化结果。"""
from __future__ import annotations

import asyncio
import heapq
from dataclasses import dataclass, field
from typing import Callable, Optional

import httpx

from ..config import settings
from . import cleaner, page_finder, robots
from .fetcher import FetchResult, fetch_rendered, fetch_static

ProgressCb = Callable[[int, str], None]


@dataclass
class CrawledPage:
    url: str
    category: str
    title: str
    text: str


@dataclass
class CrawlOutput:
    home_url: str
    final_url: str
    pages: list[CrawledPage] = field(default_factory=list)
    download_links: list[dict] = field(default_factory=list)
    news_links: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def combined_text(self, limit: int) -> str:
        chunks = []
        for page in self.pages:
            chunks.append(
                f"### 页面[{page.category}] {page.title}\nURL: {page.url}\n{page.text}"
            )
        return "\n\n".join(chunks)[:limit]


def _dedup(items: list[dict], key: str = "url") -> list[dict]:
    seen, out = set(), []
    for item in items:
        value = item.get(key)
        if value and value not in seen:
            seen.add(value)
            out.append(item)
    return out


async def _get_html(url: str, client: httpx.AsyncClient) -> FetchResult:
    """静态抓取优先；正文过短时才使用 Playwright。"""
    result = await fetch_static(url, client)
    if result.ok and result.html:
        text = cleaner.extract_main_text(result.html, url)
        if len(text) >= 400 or not settings.crawl_use_playwright:
            return result
    if settings.crawl_use_playwright:
        rendered = await fetch_rendered([url])
        candidate = rendered.get(url)
        if candidate and candidate.ok and candidate.html:
            return candidate
        if candidate and candidate.error:
            static_error = result.error or f"HTTP {result.status}"
            result.error = (
                f"静态抓取失败（{static_error}）；"
                f"浏览器渲染失败（{candidate.error}）"
            )
    return result


async def crawl_site(home_url: str, progress: Optional[ProgressCb] = None) -> CrawlOutput:
    def report(percent: int, message: str):
        if progress:
            progress(percent, message)

    out = CrawlOutput(home_url=home_url, final_url=home_url)
    async with httpx.AsyncClient(
        headers={"User-Agent": settings.crawl_user_agent},
        follow_redirects=True,
    ) as client:
        robot_parser = await robots.load_robots(home_url, client)
        if not robots.can_fetch(robot_parser, home_url):
            out.errors.append("robots.txt 禁止抓取首页")
            report(100, "robots 禁止")
            return out

        report(8, "抓取首页…")
        home = await _get_html(home_url, client)
        if not home.ok or not home.html:
            out.errors.append(f"首页抓取失败: {home.error or home.status}")
            report(100, "首页抓取失败")
            return out
        out.final_url = home.final_url
        out.pages.append(
            CrawledPage(
                url=home.final_url,
                category="home",
                title=cleaner.page_title(home.html),
                text=cleaner.extract_main_text(home.html, home.final_url),
            )
        )

        report(15, "分析高价值页面…")
        home_links = page_finder.discover(home.final_url, home.html)
        out.download_links.extend(home_links.download_links)
        out.news_links.extend(home_links.news_links)

        priority_index = {
            category: index for index, category in enumerate(page_finder.PAGE_PRIORITY)
        }
        queue: list[tuple[int, int, int, int, str, str]] = []
        queued = {home.final_url}
        crawled_final_urls = {home.final_url}
        sequence = 0

        def enqueue(links: page_finder.SiteLinks, depth: int) -> None:
            nonlocal sequence
            for category in page_finder.PAGE_PRIORITY:
                for url in links.key_pages.get(category, []):
                    if url in queued:
                        continue
                    queued.add(url)
                    sequence += 1
                    detail_rank = (
                        0
                        if depth > 1 and category in {"products", "projects", "news"}
                        else 1
                    )
                    heapq.heappush(
                        queue,
                        (
                            priority_index.get(category, 99),
                            detail_rank,
                            depth,
                            sequence,
                            url,
                            category,
                        ),
                    )

        enqueue(home_links, 1)
        target_pages = max(1, settings.crawl_max_pages)
        category_limits = {
            "about": 1,
            "products": 3,
            "projects": 3,
            "applications": 1,
            "downloads": 1,
            "technology": 1,
            "sustainability": 1,
            "news": 2,
            "network": 1,
            "history": 1,
            "philosophy": 1,
        }
        category_counts: dict[str, int] = {}

        while queue and len(out.pages) < target_pages:
            _priority, _detail_rank, depth, _seq, url, category = heapq.heappop(queue)
            if category_counts.get(category, 0) >= category_limits.get(category, 2):
                continue
            if not robots.can_fetch(robot_parser, url):
                out.errors.append(f"robots.txt 跳过: {url}")
                continue

            percent = 15 + int(68 * len(out.pages) / target_pages)
            report(percent, f"抓取 {category} 页（{len(out.pages) + 1}/{target_pages}）…")
            await asyncio.sleep(settings.crawl_delay)
            result = await _get_html(url, client)
            if not result.ok or not result.html:
                out.errors.append(f"抓取失败 {url}: {result.error or result.status}")
                continue
            if result.final_url in crawled_final_urls:
                continue
            crawled_final_urls.add(result.final_url)

            text = cleaner.extract_main_text(result.html, result.final_url)
            if text:
                category_counts[category] = category_counts.get(category, 0) + 1
                out.pages.append(
                    CrawledPage(
                        url=result.final_url,
                        category=category,
                        title=cleaner.page_title(result.html),
                        text=text,
                    )
                )

            sub_links = page_finder.discover(
                result.final_url, result.html, inherited_category=category
            )
            out.download_links.extend(sub_links.download_links)
            out.news_links.extend(sub_links.news_links)
            if depth < 3:
                enqueue(sub_links, depth + 1)

        out.download_links = _dedup(out.download_links)
        out.news_links = _dedup(out.news_links)
        report(88, f"抓取完成：{len(out.pages)} 个页面")
    return out

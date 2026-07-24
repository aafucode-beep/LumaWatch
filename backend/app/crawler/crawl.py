"""探测编排：给定入口 URL，抓取首页 + 关键页面，产出结构化抓取结果。"""
from __future__ import annotations

import asyncio
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
        for p in self.pages:
            chunks.append(f"### 页面[{p.category}] {p.title}\nURL: {p.url}\n{p.text}")
        text = "\n\n".join(chunks)
        return text[:limit]


def _dedup(items: list[dict], key: str = "url") -> list[dict]:
    seen, out = set(), []
    for it in items:
        k = it.get(key)
        if k and k not in seen:
            seen.add(k)
            out.append(it)
    return out


async def _get_html(url: str, client: httpx.AsyncClient) -> FetchResult:
    """先静态抓取；若疑似 JS 渲染（正文过短）且开启 Playwright，则渲染。"""
    res = await fetch_static(url, client)
    if res.ok and res.html:
        text = cleaner.extract_main_text(res.html, url)
        if len(text) >= 400 or not settings.crawl_use_playwright:
            return res
    if settings.crawl_use_playwright:
        rendered = await fetch_rendered([url])
        r = rendered.get(url)
        if r and r.ok and r.html:
            return r
    return res


async def crawl_site(home_url: str, progress: Optional[ProgressCb] = None) -> CrawlOutput:
    def report(pct: int, msg: str):
        if progress:
            progress(pct, msg)

    out = CrawlOutput(home_url=home_url, final_url=home_url)
    async with httpx.AsyncClient(
        headers={"User-Agent": settings.crawl_user_agent}, follow_redirects=True
    ) as client:
        rp = await robots.load_robots(home_url, client)
        if not robots.can_fetch(rp, home_url):
            out.errors.append("robots.txt 禁止抓取首页")
            report(100, "robots 禁止")
            return out

        report(10, "抓取首页…")
        home = await _get_html(home_url, client)
        if not home.ok or not home.html:
            out.errors.append(f"首页抓取失败: {home.error or home.status}")
            report(100, "首页抓取失败")
            return out
        out.final_url = home.final_url

        # 首页正文
        out.pages.append(
            CrawledPage(
                url=home.final_url,
                category="home",
                title=cleaner.page_title(home.html),
                text=cleaner.extract_main_text(home.html, home.final_url),
            )
        )

        report(25, "分析站点链接…")
        links = page_finder.discover(home.final_url, home.html)
        out.download_links.extend(links.download_links)
        out.news_links.extend(links.news_links)

        to_crawl = page_finder.select_pages_to_crawl(
            home.final_url, links, settings.crawl_max_pages
        )
        # 记录每个待抓 URL 的类别
        url_category: dict[str, str] = {}
        for cat, urls in links.key_pages.items():
            for u in urls:
                url_category.setdefault(u, cat)

        total = max(1, len(to_crawl))
        for i, u in enumerate(to_crawl):
            if not robots.can_fetch(rp, u):
                continue
            report(25 + int(60 * i / total), f"抓取 {url_category.get(u, 'page')} 页…")
            await asyncio.sleep(settings.crawl_delay)
            res = await _get_html(u, client)
            if not res.ok or not res.html:
                out.errors.append(f"抓取失败 {u}: {res.error or res.status}")
                continue
            out.pages.append(
                CrawledPage(
                    url=res.final_url,
                    category=url_category.get(u, "page"),
                    title=cleaner.page_title(res.html),
                    text=cleaner.extract_main_text(res.html, res.final_url),
                )
            )
            # 从子页面继续发现下载/新闻链接
            sub = page_finder.discover(res.final_url, res.html)
            out.download_links.extend(sub.download_links)
            out.news_links.extend(sub.news_links)

        out.download_links = _dedup(out.download_links)
        out.news_links = _dedup(out.news_links)
        report(90, "抓取完成")
    return out

"""页面识别与链接分类：从首页链接中挑出关键页面，并归类下载/新闻链接。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .fetcher import normalize_url, same_registrable_domain

# 关键页面类别 -> 匹配关键词（链接文本或 URL 路径）
PAGE_KEYWORDS: dict[str, list[str]] = {
    "about": [
        "about", "company", "who-we-are", "our-story", "corporate", "profile",
        "关于", "公司简介", "企业介绍", "关于我们",
    ],
    "products": [
        "product", "products", "solutions", "catalog", "range", "portfolio",
        "产品", "解决方案", "产品中心",
    ],
    "downloads": [
        "download", "downloads", "resource", "resources", "support", "documentation",
        "media", "assets", "literature", "下载", "资料", "支持", "文档",
    ],
    "news": [
        "news", "press", "media", "blog", "insights", "stories", "events",
        "新闻", "资讯", "动态", "媒体",
    ],
    "history": ["history", "heritage", "milestone", "历史", "发展历程"],
    "philosophy": ["philosophy", "mission", "vision", "values", "理念", "使命", "愿景"],
}

# 下载资源文件扩展名
DOWNLOAD_EXTS = {
    "pdf", "ies", "ldt", "zip", "rar", "dwg", "dxf", "rfa", "step", "stp",
    "3ds", "skp", "xls", "xlsx", "doc", "docx", "csv", "eps", "ai",
}

DOWNLOAD_TYPE_HINTS = {
    "catalog": ["catalog", "catalogue", "brochure", "样册", "画册", "产品册"],
    "ies": ["ies", "photometric", "光度", "配光"],
    "datasheet": ["datasheet", "spec", "specification", "数据表", "规格"],
    "bim": ["bim", "revit", "rfa", "cad", "dwg", "3d"],
    "certificate": ["certificate", "certification", "认证", "证书"],
    "manual": ["manual", "instruction", "installation", "手册", "说明书", "安装"],
}


@dataclass
class SiteLinks:
    key_pages: dict[str, list[str]] = field(default_factory=dict)  # 类别 -> url 列表
    download_links: list[dict] = field(default_factory=list)  # {title,url,resource_type,file_ext}
    news_links: list[dict] = field(default_factory=list)  # {title,url}


def _classify_download(text: str, url: str) -> tuple[str, str | None]:
    ext = None
    m = re.search(r"\.([a-z0-9]{2,5})(?:\?|$)", url.lower())
    if m and m.group(1) in DOWNLOAD_EXTS:
        ext = m.group(1)
    blob = f"{text} {url}".lower()
    for rtype, hints in DOWNLOAD_TYPE_HINTS.items():
        if any(h in blob for h in hints):
            return rtype, ext
    if ext == "pdf":
        return "catalog", ext
    if ext in ("ies", "ldt"):
        return "ies", ext
    return "other", ext


def discover(base_url: str, html: str, max_per_category: int = 4) -> SiteLinks:
    """从一个页面的 HTML 中发现关键页面与下载/新闻链接。"""
    soup = BeautifulSoup(html, "lxml")
    result = SiteLinks(key_pages={k: [] for k in PAGE_KEYWORDS})

    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        url = normalize_url(base_url, a["href"])
        if not url or url in seen:
            continue
        seen.add(url)
        text = " ".join(a.get_text(" ", strip=True).split())[:200]
        low_url = url.lower()
        path = urlparse(low_url).path

        # 下载链接（文件扩展名）
        m = re.search(r"\.([a-z0-9]{2,5})(?:\?|$)", low_url)
        if m and m.group(1) in DOWNLOAD_EXTS:
            rtype, ext = _classify_download(text, url)
            result.download_links.append(
                {"title": text or url.rsplit("/", 1)[-1], "url": url,
                 "resource_type": rtype, "file_ext": ext}
            )
            continue

        # 仅在同站范围内归类关键页面
        internal = same_registrable_domain(base_url, url)
        blob = f"{text} {path}".lower()

        matched_news = any(k in blob for k in PAGE_KEYWORDS["news"])
        if matched_news and internal:
            result.news_links.append({"title": text or url, "url": url})

        for cat, kws in PAGE_KEYWORDS.items():
            if cat == "news":
                continue
            if internal and any(k in blob for k in kws):
                bucket = result.key_pages[cat]
                if url not in bucket and len(bucket) < max_per_category:
                    bucket.append(url)

    return result


def select_pages_to_crawl(home_url: str, links: SiteLinks, max_pages: int) -> list[str]:
    """决定除首页外还要抓取哪些页面，按优先级取前 N 个。"""
    ordered: list[str] = []
    priority = ["about", "products", "downloads", "history", "philosophy", "news"]
    for cat in priority:
        for u in links.key_pages.get(cat, []):
            if u not in ordered and u != home_url:
                ordered.append(u)
    return ordered[: max(0, max_pages - 1)]

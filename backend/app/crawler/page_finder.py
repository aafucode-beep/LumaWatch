"""页面识别与链接分类：发现高价值页面、下载资源和真实新闻文章。"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .fetcher import normalize_url, same_registrable_domain

PAGE_KEYWORDS: dict[str, list[str]] = {
    "about": [
        "about", "company", "who-we-are", "our-story", "corporate", "profile",
        "关于", "公司简介", "企业介绍", "关于我们",
    ],
    "products": [
        "product", "products", "luminaire", "luminaires", "portfolio", "range",
        "tracklight", "downlight", "wallwash", "linear-light", "spotlight",
        "产品", "灯具", "产品中心", "产品系列",
    ],
    "projects": [
        "project", "projects", "reference", "references", "case-study", "case-studies",
        "inspiration", "项目", "案例", "工程案例", "参考项目",
    ],
    "applications": [
        "application", "applications", "solution", "solutions", "museum", "retail",
        "hospitality", "office", "workplace", "outdoor", "应用", "场景", "解决方案",
    ],
    "downloads": [
        "download", "downloads", "resource", "resources", "support", "documentation",
        "media", "assets", "literature", "catalog", "datasheet", "bim", "ies",
        "下载", "资料", "支持", "文档", "样本", "规格书",
    ],
    "technology": [
        "technology", "innovation", "optics", "control", "connectivity", "tunable-white",
        "human-centric", "lighting-technology", "技术", "光学", "控制系统", "智能照明",
    ],
    "sustainability": [
        "sustainability", "sustainable", "environment", "circular", "responsibility",
        "certificate", "certification", "可持续", "环保", "认证", "社会责任",
    ],
    "network": [
        "contact", "locations", "offices", "partners", "distributors", "dealers",
        "showrooms", "where-to-buy", "联系", "办事处", "经销商", "展厅", "销售网络",
    ],
    "news": [
        "news", "press", "media", "blog", "insights", "stories", "events", "article",
        "新闻", "资讯", "动态", "媒体", "文章",
    ],
    "history": ["history", "heritage", "milestone", "timeline", "历史", "发展历程"],
    "philosophy": [
        "philosophy", "mission", "vision", "values", "purpose",
        "理念", "使命", "愿景", "价值观",
    ],
}

PAGE_PRIORITY = [
    "about", "products", "projects", "applications", "sustainability",
    "news", "downloads", "technology", "network", "history", "philosophy",
]

DOWNLOAD_EXTS = {
    "pdf", "ies", "ldt", "zip", "rar", "dwg", "dxf", "rfa", "step", "stp",
    "3ds", "skp", "xls", "xlsx", "doc", "docx", "csv", "eps", "ai",
}

NON_PAGE_EXTS = {
    "jpg", "jpeg", "png", "gif", "webp", "svg", "ico",
    "mp4", "webm", "mp3", "wav", "css", "js", "json", "xml",
    "woff", "woff2", "ttf", "eot",
}

DOWNLOAD_TYPE_HINTS = {
    "catalog": ["catalog", "catalogue", "brochure", "样册", "画册", "产品册"],
    "ies": ["ies", "ldt", "photometric", "光度", "配光"],
    "datasheet": ["datasheet", "spec", "specification", "数据表", "规格"],
    "bim": ["bim", "revit", "rfa", "cad", "dwg", "3d"],
    "certificate": ["certificate", "certification", "认证", "证书"],
    "manual": ["manual", "instruction", "installation", "手册", "说明书", "安装"],
}

NEWS_NAV_LABELS = {
    "news", "press", "media", "blog", "insights", "stories", "events",
    "seminars and events", "press releases", "newsletter", "subscribe",
    "subscribe to the newsletter", "more", "read more", "all news",
    "新闻", "资讯", "动态", "媒体", "订阅", "查看更多",
}


@dataclass
class SiteLinks:
    key_pages: dict[str, list[str]] = field(default_factory=dict)
    download_links: list[dict] = field(default_factory=list)
    news_links: list[dict] = field(default_factory=list)


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


def _looks_like_news_item(text: str, url: str) -> bool:
    label = " ".join(text.lower().split()).strip(" -–—|>")
    if not label or label in NEWS_NAV_LABELS or len(label) < 8:
        return False
    path = urlparse(url).path.lower().rstrip("/")
    parts = [p for p in path.split("/") if p]
    if len(parts) < 2:
        return False
    if re.search(r"/(?:19|20)\d{2}(?:/|[-_])", path):
        return True
    article_markers = ("article", "story", "press-release", "news-detail", "news/")
    if any(marker in path for marker in article_markers) and len(parts[-1]) >= 8:
        return True
    return len(parts) >= 3 and len(label) >= 18 and any(
        marker in path for marker in ("news", "press", "blog", "insight", "stories")
    )


def discover(
    base_url: str,
    html: str,
    max_per_category: int = 8,
    inherited_category: str | None = None,
) -> SiteLinks:
    """从页面中发现关键页面；具体新闻与栏目入口分开处理。"""
    soup = BeautifulSoup(html, "lxml")
    result = SiteLinks(key_pages={k: [] for k in PAGE_KEYWORDS})
    inherited_candidates: list[str] = []
    base_path = urlparse(base_url).path.rstrip("/") + "/"

    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        url = normalize_url(base_url, a["href"])
        if not url or url in seen:
            continue
        seen.add(url)
        text = " ".join(a.get_text(" ", strip=True).split())[:240]
        low_url = url.lower()
        path = urlparse(low_url).path

        m = re.search(r"\.([a-z0-9]{2,5})(?:\?|$)", low_url)
        if m and m.group(1) in DOWNLOAD_EXTS:
            rtype, ext = _classify_download(text, url)
            result.download_links.append(
                {
                    "title": text or url.rsplit("/", 1)[-1],
                    "url": url,
                    "resource_type": rtype,
                    "file_ext": ext,
                }
            )
            continue

        if m and m.group(1) in NON_PAGE_EXTS:
            continue

        if not same_registrable_domain(base_url, url):
            continue

        blob = f"{text} {path}".lower()
        is_news_item = _looks_like_news_item(text, url)
        news_slug = path.rstrip("/").rsplit("/", 1)[-1]
        is_news_landing = news_slug in {
            "news", "press", "media", "blog", "stories", "events", "news--events"
        }
        matched_categories = [
            category
            for category, keywords in PAGE_KEYWORDS.items()
            if any(keyword in blob for keyword in keywords)
        ]
        for category in matched_categories:
            if category == "news" and not (is_news_item or is_news_landing):
                continue
            bucket = result.key_pages[category]
            if url not in bucket and len(bucket) < max_per_category:
                bucket.append(url)

        if is_news_item:
            result.news_links.append({"title": text, "url": url})

        label = text.lower()
        if inherited_category == "products" and (
            "explore the full line" in label
            or re.search(r"\b\d[\d,.]*\s*lm\b", label)
        ):
            inherited_candidates.append(url)
        elif inherited_category == "projects" and path.startswith(base_path):
            if path != base_path and "/all-" not in path:
                inherited_candidates.append(url)
        elif inherited_category == "news" and is_news_item:
            inherited_candidates.append(url)

    if inherited_category in {"products", "projects", "news"}:
        existing = result.key_pages[inherited_category]
        result.key_pages[inherited_category] = list(
            dict.fromkeys(inherited_candidates + existing)
        )[:max_per_category]

    return result


def select_pages_to_crawl(home_url: str, links: SiteLinks, max_pages: int) -> list[str]:
    """按情报价值排序首页发现的候选页面。"""
    ordered: list[str] = []
    for category in PAGE_PRIORITY:
        for url in links.key_pages.get(category, []):
            if url not in ordered and url != home_url:
                ordered.append(url)
    return ordered[: max(0, max_pages - 1)]

"""正文清洗：从 HTML 抽取主要文本，控制长度。"""
from __future__ import annotations

from bs4 import BeautifulSoup


def extract_main_text(html: str, url: str = "") -> str:
    if not html:
        return ""
    # 优先 trafilatura（对文章/正文页效果好）
    try:
        import trafilatura

        text = trafilatura.extract(
            html, include_links=False, include_comments=False, favor_recall=True
        )
        if text and len(text.strip()) > 80:
            return text.strip()
    except Exception:  # noqa: BLE001
        pass

    # 兜底：BeautifulSoup 去脚本样式后取文本
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    lines = [ln for ln in text.splitlines() if len(ln.strip()) > 1]
    return "\n".join(lines).strip()


def page_title(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    if soup.title and soup.title.string:
        return soup.title.string.strip()[:255]
    h1 = soup.find("h1")
    return h1.get_text(strip=True)[:255] if h1 else ""

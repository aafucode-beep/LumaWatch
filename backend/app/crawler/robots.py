"""robots.txt 检查（可通过配置关闭）。"""
from __future__ import annotations

from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx

from ..config import settings


async def load_robots(base_url: str, client: httpx.AsyncClient) -> RobotFileParser | None:
    if not settings.crawl_respect_robots:
        return None
    parsed = urlparse(base_url)
    robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
    rp = RobotFileParser()
    try:
        resp = await client.get(robots_url, timeout=10, follow_redirects=True)
        if resp.status_code >= 400:
            return None
        rp.parse(resp.text.splitlines())
        return rp
    except Exception:  # noqa: BLE001
        return None


def can_fetch(rp: RobotFileParser | None, url: str) -> bool:
    if rp is None:
        return True
    try:
        return rp.can_fetch(settings.crawl_user_agent, url)
    except Exception:  # noqa: BLE001
        return True

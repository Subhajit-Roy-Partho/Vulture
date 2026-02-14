from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def fetch_job_text(url: str, timeout_sec: int = 30) -> str:
    try:
        response = requests.get(url, timeout=timeout_sec, headers={"User-Agent": USER_AGENT})
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to fetch job URL %s: %s", url, exc)
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.extract()

    text = soup.get_text("\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

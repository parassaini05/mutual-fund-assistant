"""
ingestion/scraper.py — Web scraper for Groww mutual fund pages.
"""

import html
import logging
import random
import re
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import requests
from bs4 import BeautifulSoup

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import FUND_URLS

try:
    from ingestion.cleaner import clean_html as _clean_html_deep
except ImportError:
    def _clean_html_deep(html): return html

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("scraper")

REQUEST_TIMEOUT: int = 15
MAX_RETRIES: int = 3
RETRY_BASE_DELAY: float = 2.0
MIN_DELAY_BETWEEN_PAGES: float = 2.0
MAX_DELAY_BETWEEN_PAGES: float = 5.0
MIN_CONTENT_CHARS: int = 500

REQUIRED_KEYWORDS: list[str] = ["expense ratio", "exit load", "sip", "nav", "risk"]

BOILERPLATE_PATTERNS: list[str] = [
    r"download app", r"login", r"sign up", r"cookie",
    r"privacy policy", r"terms of service",
]

HEADERS: dict[str, str] = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

DISCARD_TAGS: set[str] = {
    "script", "style", "noscript", "nav", "footer", "head",
    "button", "svg", "path", "iframe", "form", "input", "select",
    "meta", "link", "aside",
}


@dataclass
class ScrapedPage:
    fund_name: str
    amc: str
    category: str
    source_url: str
    scraped_date: str
    raw_text: str
    keyword_hits: list[str] = field(default_factory=list)
    is_valid: bool = True


@dataclass
class ScrapeResult:
    pages: list[ScrapedPage] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    @property
    def success_count(self) -> int: return len(self.pages)
    @property
    def failure_count(self) -> int: return len(self.failures)


def _fetch_html_playwright(url: str) -> Optional[str]:
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        logger.warning("Playwright not installed.")
        return None

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(user_agent=HEADERS["User-Agent"])
            page = context.new_page()
            page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}", lambda route: route.abort())
            logger.info(f"  [Playwright] Navigating to: {url}")
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            try:
                page.wait_for_function(
                    "() => document.body.innerText.toLowerCase().includes('expense ratio') || document.body.innerText.toLowerCase().includes('exit load')",
                    timeout=15000,
                )
            except PWTimeout:
                pass
            html_content = page.content()
            browser.close()
            return html_content
    except Exception as e:
        logger.error(f"  [Playwright] Failed: {e}")
        return None


def _fetch_html_requests(url: str) -> Optional[str]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.exceptions.HTTPError as e:
            if getattr(e.response, "status_code", None) == 429:
                time.sleep(int(e.response.headers.get("Retry-After", 10)))
            else:
                time.sleep(RETRY_BASE_DELAY * attempt)
        except Exception:
            time.sleep(RETRY_BASE_DELAY * attempt)
    return None


def _fetch_html(url: str) -> Optional[str]:
    html_content = _fetch_html_playwright(url)
    if html_content and len(html_content) > MIN_CONTENT_CHARS:
        return html_content
    return _fetch_html_requests(url)


def _clean_html(raw_html: str) -> str:
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag_name in DISCARD_TAGS:
        for tag in soup.find_all(tag_name):
            tag.decompose()
    raw_text = soup.get_text(separator="\n", strip=True)
    raw_text = html.unescape(raw_text)
    raw_text = re.sub(r"\n{3,}", "\n\n", raw_text)
    raw_text = re.sub(r"[ \t]{2,}", " ", raw_text)
    filtered = [line.strip() for line in raw_text.splitlines() if not any(re.search(p, line.lower()) for p in BOILERPLATE_PATTERNS) and line.strip()]
    return "\n".join(filtered)


def _validate_content(text: str, fund_name: str) -> tuple[bool, list[str]]:
    if len(text) < MIN_CONTENT_CHARS: return False, []
    text_lower = text.lower()
    found = [kw for kw in REQUIRED_KEYWORDS if kw in text_lower]
    return len(found) >= 3, found


def scrape_fund_page(fund: dict) -> Optional[ScrapedPage]:
    url = fund["url"]
    fund_name = fund["fund_name"]
    raw_html = _fetch_html(url)
    if not raw_html: return None
    try:
        clean_text = _clean_html_deep(raw_html)
        if clean_text == raw_html: clean_text = _clean_html(raw_html)
    except:
        clean_text = _clean_html(raw_html)
    is_valid, hits = _validate_content(clean_text, fund_name)
    return ScrapedPage(fund_name, fund["amc"], fund["category"], url, date.today().isoformat(), clean_text, hits, is_valid)


def scrape_all_funds(fund_list=None) -> ScrapeResult:
    fund_list = fund_list or FUND_URLS
    result = ScrapeResult()
    for idx, fund in enumerate(fund_list, 1):
        page = scrape_fund_page(fund)
        if page: result.pages.append(page)
        else: result.failures.append({"fund_name": fund["fund_name"], "url": fund["url"], "reason": "Failed"})
        if idx < len(fund_list): time.sleep(random.uniform(2, 5))
    return result

if __name__ == "__main__":
    scrape_all_funds()

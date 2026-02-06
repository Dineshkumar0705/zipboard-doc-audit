import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from app.utils.helpers import clean_text

BASE_URL = "https://help.zipboard.co"

HEADERS = {
    "User-Agent": "ZipBoardDocAuditBot/1.0 (+https://help.zipboard.co)"
}

REQUEST_TIMEOUT = 15
REQUEST_DELAY_SEC = 0.6  # slightly safer for HelpScout


class ZipboardArticleScraper:
    """
    Pure web scraper for zipBoard Help Center.

    Responsibilities:
    1. Discover ALL article URLs via HelpScout collections
    2. Scrape ONE article at a time

    Design guarantees:
    - Never crashes pipeline
    - Network failures are safely skipped
    - Deterministic outputs
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    # ==================================================
    # ARTICLE LINK DISCOVERY
    # ==================================================
    def get_all_article_links(self) -> List[str]:
        print("🔍 Discovering Help Center collections...")

        homepage_html = self._safe_get(BASE_URL)
        if not homepage_html:
            print("⚠️ Homepage fetch failed")
            return []

        soup = BeautifulSoup(homepage_html, "lxml")

        collection_links = set()

        for a in soup.select("a[href]"):
            href = a.get("href", "").strip()
            if "/collection/" in href:
                collection_links.add(self._absolute_url(href))

        print(f"📂 Found {len(collection_links)} collections")

        article_links = set()

        for collection_url in collection_links:
            time.sleep(REQUEST_DELAY_SEC)

            html = self._safe_get(collection_url)
            if not html:
                continue

            col_soup = BeautifulSoup(html, "lxml")

            for a in col_soup.select("a[href]"):
                href = a.get("href", "").strip()
                if "/article/" in href:
                    article_links.add(self._absolute_url(href))

        print(f"✅ Discovered {len(article_links)} unique article URLs")
        return sorted(article_links)

    # ==================================================
    # SINGLE ARTICLE SCRAPING (FAIL-SAFE)
    # ==================================================
    def scrape_article(self, url: str, article_id: str) -> Dict:
        print(f"📄 Scraping {article_id}")

        time.sleep(REQUEST_DELAY_SEC)

        html = self._safe_get(url)

        # --------------------------------------------------
        # 🚨 SAFE FALLBACK (CRITICAL FIX)
        # --------------------------------------------------
        if not html:
            print(f"⚠️ Skipped article due to fetch failure: {url}")

            return {
                "article_id": article_id,
                "title": "Unavailable Article",
                "category": "Unknown",
                "url": url,
                "raw_text": "",
                "has_images": False,
                "fetch_failed": True
            }

        soup = BeautifulSoup(html, "lxml")

        # ----------------------------------------------
        # Title
        # ----------------------------------------------
        title_el = soup.find("h1")
        title = title_el.get_text(strip=True) if title_el else "Untitled"

        # ----------------------------------------------
        # Main content extraction
        # ----------------------------------------------
        content_nodes = soup.select(
            "article p, article li, article h2, article h3"
        )

        blocks = []

        for node in content_nodes:
            text = node.get_text(" ", strip=True)
            if not text:
                continue

            lower = text.lower()

            if any(
                noise in lower
                for noise in [
                    "contact us",
                    "powered by helpscout",
                    "was this article helpful",
                ]
            ):
                continue

            blocks.append(text)

        raw_text = clean_text(" ".join(blocks))

        # ----------------------------------------------
        # Image detection (content images only)
        # ----------------------------------------------
        has_images = False
        for img in soup.select("article img"):
            src = img.get("src", "")
            if src and "icon" not in src.lower():
                has_images = True
                break

        return {
            "article_id": article_id,
            "title": title,
            "category": "Unknown",  # inferred later
            "url": url,
            "raw_text": raw_text,
            "has_images": has_images
        }

    # ==================================================
    # INTERNAL HELPERS
    # ==================================================
    def _safe_get(self, url: str) -> Optional[str]:
        """
        Safe HTTP GET wrapper.
        Returns HTML text or None on failure.
        """
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"⚠️ Failed to fetch {url}: {e}")
            return None

    def _absolute_url(self, href: str) -> str:
        """
        Converts relative URLs to absolute URLs.
        """
        if href.startswith("http"):
            return href
        return BASE_URL + href
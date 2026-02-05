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
REQUEST_DELAY_SEC = 0.5   # prevents throttling & “stuck” feeling


class ZipboardArticleScraper:
    """
    Pure web scraper for zipBoard Help Center.

    Responsibilities:
    1. Discover ALL article URLs via Help Scout collections
    2. Scrape ONE article at a time

    Explicitly does NOT:
    - Run AI
    - Batch process
    - Write files
    - Touch spreadsheets
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    # ==================================================
    # ARTICLE LINK DISCOVERY
    # ==================================================
    def get_all_article_links(self) -> List[str]:
        print("🔍 Discovering Help Scout collections...")

        homepage_html = self._safe_get(BASE_URL)
        if not homepage_html:
            return []

        soup = BeautifulSoup(homepage_html, "lxml")

        # ----------------------------------------------
        # Step 1: Collect collection URLs
        # ----------------------------------------------
        collection_links = set()

        for a in soup.select("a[href]"):
            href = a.get("href", "").strip()
            if "/collection/" in href:
                collection_links.add(self._absolute_url(href))

        print(f"📂 Found {len(collection_links)} collections")

        # ----------------------------------------------
        # Step 2: Crawl collections → article URLs
        # ----------------------------------------------
        article_links = set()

        for collection_url in collection_links:
            time.sleep(REQUEST_DELAY_SEC)

            collection_html = self._safe_get(collection_url)
            if not collection_html:
                continue

            col_soup = BeautifulSoup(collection_html, "lxml")

            for a in col_soup.select("a[href]"):
                href = a.get("href", "").strip()
                if "/article/" in href:
                    article_links.add(self._absolute_url(href))

        print(f"✅ Discovered {len(article_links)} article URLs")
        return sorted(article_links)

    # ==================================================
    # SINGLE ARTICLE SCRAPING
    # ==================================================
    def scrape_article(self, url: str, article_id: str) -> Dict:
        print(f"📄 Scraping {article_id}")

        time.sleep(REQUEST_DELAY_SEC)

        article_html = self._safe_get(url)
        if not article_html:
            raise RuntimeError(f"Failed to fetch article: {url}")

        soup = BeautifulSoup(article_html, "lxml")

        # ----------------------------------------------
        # Title
        # ----------------------------------------------
        title_el = soup.find("h1")
        title = title_el.get_text(strip=True) if title_el else "Untitled"

        # ----------------------------------------------
        # Main content (remove footer noise)
        # ----------------------------------------------
        paragraphs = []

        for p in soup.find_all("p"):
            text = p.get_text(" ", strip=True)
            if not text:
                continue

            # Skip HelpScout boilerplate
            if "contact us" in text.lower():
                continue
            if "powered by helpscout" in text.lower():
                continue

            paragraphs.append(text)

        raw_text = clean_text(" ".join(paragraphs))

        # ----------------------------------------------
        # Media detection
        # ----------------------------------------------
        has_images = bool(soup.find("img"))

        return {
            "article_id": article_id,
            "title": title,
            "category": "Unknown",   # filled later
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
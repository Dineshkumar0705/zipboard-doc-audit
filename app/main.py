import json
import time
from pathlib import Path

from app.scraper.article_scraper import ZipboardArticleScraper
from app.processors.json_structurer import ArticleJSONStructurer
from app.processors.gap_detector import GapDetector
from app.sheets.sheet_manager import SheetManager
from app.config import MAX_ARTICLES_PER_RUN

# --------------------------------------------------
# PATH CONFIG
# --------------------------------------------------
RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


# --------------------------------------------------
# UTILS
# --------------------------------------------------
def already_processed(article_id: str) -> bool:
    """
    Returns True if article has already been processed.
    Processed JSON is the single source of truth.
    """
    return (PROCESSED_DIR / f"{article_id}.json").exists()


def save_json(path: Path, data: dict):
    """
    Safely writes JSON to disk.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# --------------------------------------------------
# MAIN ORCHESTRATOR
# --------------------------------------------------
def main():
    print("\n🚀 Starting zipBoard documentation audit run\n")

    # Ensure directories exist
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize components (HF-only pipeline)
    scraper = ZipboardArticleScraper()
    structurer = ArticleJSONStructurer()
    sheet_manager = SheetManager()

    # --------------------------------------------------
    # STEP 1: Discover article URLs
    # --------------------------------------------------
    print("🔍 Discovering articles...")
    all_links = scraper.get_all_article_links()

    if not all_links:
        print("⚠️ No article links found. Exiting.\n")
        return

    print(f"📦 Total discovered articles: {len(all_links)}")

    # --------------------------------------------------
    # STEP 2: Controlled batching (NO SKIP by default)
    # --------------------------------------------------
    links_to_process = all_links[:MAX_ARTICLES_PER_RUN]
    print(f"🎯 Articles scheduled this run: {len(links_to_process)}\n")

    processed_count = 0

    # --------------------------------------------------
    # STEP 3–5: Process articles one by one
    # --------------------------------------------------
    for idx, url in enumerate(links_to_process, start=1):
        article_id = f"KB-{idx:03d}"

        print(f"\n➡️ Processing {article_id}")

        try:
            # -------------------------------
            # SCRAPE
            # -------------------------------
            print("   🕷️ Scraping article...")
            raw_article = scraper.scrape_article(url, article_id)
            save_json(RAW_DIR / f"{article_id}.json", raw_article)

            # -------------------------------
            # STRUCTURE (HF-based, deterministic)
            # -------------------------------
            print("   🤖 Running semantic analysis (HF)...")
            structured_article = structurer.structure_article(raw_article)
            save_json(PROCESSED_DIR / f"{article_id}.json", structured_article)

            # -------------------------------
            # GOOGLE SHEETS SYNC
            # -------------------------------
            print("   📊 Syncing to Google Sheets...")
            sheet_manager.upsert(structured_article)

            processed_count += 1
            print(f"✅ {article_id} processed successfully")

            # Small delay → prevents API burst & UI freeze feeling
            time.sleep(1)

        except Exception as e:
            print(f"❌ Failed processing {article_id}")
            print(f"   Reason: {e}")

    print(f"\n🏁 Article processing complete. Count: {processed_count}\n")

    # --------------------------------------------------
    # STEP 6: AGGREGATED GAP ANALYSIS
    # --------------------------------------------------
    print("🧠 Running gap aggregation analysis...")

    try:
        gap_detector = GapDetector(PROCESSED_DIR)
        gap_analysis = gap_detector.detect_gaps(top_n=5)

        if gap_analysis:
            print("   📌 Writing gap analysis to spreadsheet...")
            sheet_manager.upsert_gap_analysis(gap_analysis)
            print("✅ Gap analysis pushed to spreadsheet")
        else:
            print("⚠️ No gaps detected")

    except Exception as e:
        print("❌ Gap analysis failed")
        print(f"   Reason: {e}")

    print("\n🎉 zipBoard documentation audit completed successfully\n")


# --------------------------------------------------
# ENTRY POINT
# --------------------------------------------------
if __name__ == "__main__":
    main()
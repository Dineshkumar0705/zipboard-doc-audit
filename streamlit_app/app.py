# ==================================================
# BOOTSTRAP (MUST BE FIRST)
# ==================================================
import sys
import time
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# ==================================================
# IMPORTS
# ==================================================
import streamlit as st

from app.scraper.article_scraper import ZipboardArticleScraper
from app.processors.json_structurer import ArticleJSONStructurer
from app.sheets.sheet_manager import SheetManager

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="zipBoard Documentation Intelligence",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================================================
# THEME – MONOCHROME HARMONY (LIGHT)
# ==================================================
st.markdown("""
<style>

/* Force light background */
html, body, [data-testid="stAppViewContainer"] {
    background-color: #e8eddf !important;
}

/* Layout */
.block-container {
    padding-top: 2.5rem;
}

/* Headings */
h1, h2, h3, h4 {
    color: #242423 !important;
    font-weight: 700;
}

/* Text */
p, span, div, label {
    color: #333533 !important;
}

/* Cards */
.card {
    background-color: #cfdbd5;
    padding: 1.4rem;
    border-radius: 14px;
    margin-bottom: 1.4rem;
    box-shadow: 0 6px 18px rgba(0,0,0,0.06);
}

/* Badges */
.badge {
    display: inline-block;
    background-color: #f5cb5c;
    color: #242423;
    padding: 0.35rem 0.75rem;
    border-radius: 8px;
    font-size: 0.75rem;
    font-weight: 700;
    margin-right: 0.4rem;
}

/* Buttons */
.stButton>button {
    background-color: #f5cb5c !important;
    color: #242423 !important;
    border-radius: 10px;
    font-weight: 700;
    padding: 0.7rem 1.6rem;
    border: none;
}

/* Progress bar */
.stProgress > div > div > div > div {
    background-color: #f5cb5c;
}

/* Inputs */
input, textarea {
    background-color: #ffffff !important;
    color: #333533 !important;
    border-radius: 10px !important;
}

/* Table */
thead tr th {
    background-color: #cfdbd5 !important;
    color: #242423 !important;
}

tbody tr td {
    background-color: #ffffff !important;
    color: #333533 !important;
}

</style>
""", unsafe_allow_html=True)

# ==================================================
# HEADER
# ==================================================
st.title("zipBoard Documentation Intelligence")
st.markdown(
    "<span class='badge'>Audit</span>"
    "<span class='badge'>Coverage</span>"
    "<span class='badge'>Gap Detection</span>",
    unsafe_allow_html=True
)

# ==================================================
# INIT CORE SERVICES (CACHED)
# ==================================================
@st.cache_resource
def init_services():
    return (
        ZipboardArticleScraper(),
        ArticleJSONStructurer(),
        SheetManager()
    )

scraper, structurer, sheet_manager = init_services()

RAW_DIR = ROOT_DIR / "data/raw"
PROCESSED_DIR = ROOT_DIR / "data/processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# ==================================================
# HELPERS
# ==================================================
def is_valid_zipboard_url(url: str) -> bool:
    return url.startswith("https://help.zipboard.co/article/")

def already_processed(url: str) -> bool:
    for f in PROCESSED_DIR.glob("*.json"):
        try:
            if url in f.read_text():
                return True
        except Exception:
            pass
    return False

# ==================================================
# MODE SELECTION
# ==================================================
mode = st.radio(
    "Select Analysis Mode",
    ["Single URL", "Batch URLs"],
    horizontal=True
)

# ==================================================
# INPUT PANEL
# ==================================================
with st.container():
    st.markdown("<div class='card'>", unsafe_allow_html=True)

    if mode == "Single URL":
        urls = [
            st.text_input(
                "🔗 zipBoard Help Article URL",
                placeholder="https://help.zipboard.co/article/123-adding-a-manager-account"
            )
        ]
    else:
        urls = st.text_area(
            "📋 Paste zipBoard article URLs (one per line)",
            height=180,
            placeholder=(
                "https://help.zipboard.co/article/122-adding-a-collaborator-or-reviewer-account\n"
                "https://help.zipboard.co/article/123-adding-a-manager-account"
            )
        ).splitlines()

    analyze_btn = st.button("▶️ Analyze")

    st.markdown("</div>", unsafe_allow_html=True)

urls = [u.strip() for u in urls if u.strip()]

# ==================================================
# ANALYSIS PIPELINE
# ==================================================
if analyze_btn and urls:
    progress = st.progress(0.0)
    status_box = st.empty()

    table_data = []
    total = len(urls)
    processed = skipped = failed = 0

    for idx, url in enumerate(urls, start=1):
        progress.progress(idx / total)

        if not is_valid_zipboard_url(url):
            table_data.append([url, "❌ Invalid (use /article/ URL)"])
            failed += 1
            status_box.table(table_data)
            continue

        if already_processed(url):
            table_data.append([url, "⏭️ Skipped (already analyzed)"])
            skipped += 1
            status_box.table(table_data)
            continue

        try:
            article_id = f"KB-{int(time.time())}-{idx}"

            raw = scraper.scrape_article(url, article_id)
            (RAW_DIR / f"{article_id}.json").write_text(
                json.dumps(raw, indent=2),
                encoding="utf-8"
            )

            structured = structurer.structure_article(raw)
            (PROCESSED_DIR / f"{article_id}.json").write_text(
                json.dumps(structured, indent=2),
                encoding="utf-8"
            )

            sheet_manager.upsert(structured)

            table_data.append([url, "✅ Processed"])
            processed += 1

        except Exception as e:
            table_data.append([url, "❌ Failed"])
            failed += 1

        status_box.table(table_data)
        time.sleep(0.4)  # prevents UI freeze

    # ==================================================
    # SUMMARY
    # ==================================================
    st.success("🎉 Analysis completed successfully")
    st.markdown(
        f"""
        **Summary**
        - ✅ Processed: {processed}  
        - ⏭️ Skipped: {skipped}  
        - ❌ Failed: {failed}
        """
    )

    # ==================================================
    # SPREADSHEET VIEW
    # ==================================================
    st.subheader("📊 Live Spreadsheet View")

st.components.v1.iframe(
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vQJz3W0LnpZYwoplFZ7359gdj2Kl4C26snAHIf7cdOmXjze5--VFNMBx8k8y2q84r8hm8w4LNABqALZ/pubhtml",
    height=600,
    scrolling=True
)
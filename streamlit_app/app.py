# ==================================================
# BOOTSTRAP
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
from app.processors.gap_analysis_engine import GapAnalysisEngine
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
# GLOBAL THEME
# ==================================================
st.markdown("""
<style>
html, body, [data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #eef1ec 0%, #e4e9e0 100%) !important;
}
.block-container { padding: 3rem; max-width: 1200px; }
h1,h2,h3 { color:#111827!important; font-weight:800; }
p,label,span { color:#374151!important; }
.card {
    background:#fff; padding:1.8rem; border-radius:18px;
    box-shadow:0 16px 40px rgba(0,0,0,.08); margin-bottom:2rem;
}
.badge {
    background:linear-gradient(135deg,#facc15,#fde047);
    padding:.35rem .8rem; border-radius:999px;
    font-size:.72rem; font-weight:700; margin-right:.4rem;
}
.stButton>button {
    background:linear-gradient(135deg,#facc15,#fde047)!important;
    color:#1f2937!important; border-radius:14px;
    font-weight:800; padding:.75rem 1.9rem;
}
input,textarea {
    background:#fff!important; color:#111827!important;
    border-radius:14px!important; border:1px solid #d1d5db!important;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# HEADER
# ==================================================
st.markdown("""
<div class="card">
<h1 style="font-size:2.8rem;margin-bottom:.4rem;">
zipBoard Documentation Intelligence
</h1>
<div style="margin-bottom:1rem;">
<span class="badge">Audit</span>
<span class="badge">Coverage</span>
<span class="badge">Gap Detection</span>
</div>
<p style="max-width:780px;font-size:1.05rem;line-height:1.65;">
Analyze zipBoard Help Center articles and surface high-impact documentation gaps.
</p>
</div>
""", unsafe_allow_html=True)

# ==================================================
# INIT SERVICES
# ==================================================
@st.cache_resource
def init_services():
    return ZipboardArticleScraper(), ArticleJSONStructurer(), SheetManager()

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
st.markdown("### 🔍 Analysis Mode")
mode = st.radio(
    "Select mode",
    ["Single URL", "Batch URLs"],
    horizontal=True,
    label_visibility="collapsed"
)

# ==================================================
# INPUT PANEL
# ==================================================
st.markdown("<div class='card'>", unsafe_allow_html=True)

if mode == "Single URL":
    urls = [st.text_input(
        "zipBoard Help Article URL",
        placeholder="https://help.zipboard.co/article/71-how-do-i-remove-zipboards-integration-with-slack"
    )]
else:
    urls = st.text_area(
        "zipBoard Help Article URLs (one per line)",
        height=160
    ).splitlines()

urls = [u.strip() for u in urls if u.strip()]
analyze_btn = st.button("▶ Analyze Documentation", disabled=not urls)
st.markdown("</div>", unsafe_allow_html=True)

# ==================================================
# ANALYSIS PIPELINE
# ==================================================
if analyze_btn and urls:
    progress = st.progress(0.0)
    status = st.empty()
    results = []

    processed = skipped = failed = 0
    total = len(urls)

    for i, url in enumerate(urls, 1):
        progress.progress(i / total)

        if not is_valid_zipboard_url(url):
            results.append([url, "❌ Invalid URL"])
            failed += 1
            status.table(results)
            continue

        if already_processed(url):
            results.append([url, "⏭️ Already analyzed"])
            skipped += 1
            status.table(results)
            continue

        article_id = f"KB-{int(time.time())}-{i}"

        try:
            raw = scraper.scrape_article(url, article_id)
            (RAW_DIR / f"{article_id}.json").write_text(json.dumps(raw, indent=2))

            structured = structurer.structure_article(raw)
            (PROCESSED_DIR / f"{article_id}.json").write_text(json.dumps(structured, indent=2))

            sheet_manager.upsert(structured)
            results.append([url, "✅ Processed"])
            processed += 1

        except Exception as e:
            results.append([url, "❌ Failed to fetch"])
            failed += 1

        status.table(results)
        time.sleep(0.3)

    # ==================================================
    # GAP ANALYSIS (FINAL & CORRECT)
    # ==================================================
    st.markdown("### 🧠 Running Gap Analysis")

    gap_engine = GapAnalysisEngine(
        processed_dir=PROCESSED_DIR,
        sheet_manager=sheet_manager
    )
    gap_engine.run(top_n=5)

    st.success("✅ Gap Analysis sheet updated successfully")

    st.markdown(f"""
    **Run Summary**
    - ✅ Processed: {processed}
    - ⏭️ Skipped: {skipped}
    - ❌ Failed: {failed}
    """)

    st.components.v1.iframe(
        "https://docs.google.com/spreadsheets/d/e/2PACX-1vQJz3W0LnpZYwoplFZ7359gdj2Kl4C26snAHIf7cdOmXjze5--VFNMBx8k8y2q84r8hm8w4LNABqALZ/pubhtml",
        height=820,
        scrolling=True
    )
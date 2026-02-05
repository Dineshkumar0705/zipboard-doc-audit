# zipBoard Documentation Audit & Gap Detection System

## Overview
This project is an **AI-powered documentation intelligence system** built to audit the zipBoard Help Center.  
It automatically catalogs help articles, extracts structured metadata, detects documentation gaps, and maintains a live, continuously updated Google Sheets knowledge base.

The system is designed to be **quota-safe, deterministic, scalable, and UI-driven**, balancing AI inference with rule-based heuristics for reliability.

---

## Problem Statement
Modern SaaS documentation grows fast but degrades silently:
- Missing prerequisites
- Unclear limitations
- Repeated user confusion
- No visibility into documentation gaps

zipBoard’s Help Center needed:
- A structured catalog of articles
- Automated gap detection
- Actionable insights for documentation improvement
- A system that scales without manual effort

---

## Solution
An end-to-end **documentation audit pipeline** with:
- Automated scraping
- AI-based topic understanding
- Gap aggregation across articles
- Live spreadsheet sync
- Streamlit UI for single & batch analysis

---

## Key Features
- 🔍 **Automated Help Center Scraping**
- 🧠 **AI-powered Topic Extraction (Hugging Face)**
- 🧩 **Documentation Gap Detection**
- 📊 **Live Google Sheets Sync**
- 🌐 **Streamlit UI**
  - Single URL analysis
  - Batch URL ingestion
  - Duplicate detection
  - Progress indicators
- ⚡ **Quota-safe & deterministic**
- 🔁 **Idempotent updates (no duplicates)**

---

## Architecture

Trigger (UI / Batch)
↓
Article Scraper
↓
Semantic Analyzer (HF + Heuristics)
↓
Gap Detector (Aggregated Insights)
↓
Google Sheets (Source of Truth)
↓
Streamlit UI (Visualization)

---

## Tech Stack
- **Python**
- **Hugging Face Inference API**
- **Streamlit**
- **Google Sheets API**
- **BeautifulSoup**
- **Requests**

---

## Data Model (Article Catalog)
Each article is stored with:
- Article ID
- Title
- Category
- URL
- Content Type
- Word Count
- Screenshot Presence
- Topics Covered
- Gaps Identified
- Severity & Risk Level

---

## Gap Detection Logic
Gaps are detected per article using semantic QA:
- Missing prerequisites
- Missing common errors
- Missing limitations

Gaps are then **aggregated across all articles** to surface:
- Common documentation failures
- High-impact missing guides
- Prioritized improvement areas

---

## How to Run Locally

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run Streamlit UI
streamlit run streamlit_app/app.py

Required environment variables:
	•	HF_API_TOKEN
	•	GOOGLE_SHEET_ID

⸻

Streamlit UI Capabilities
	•	Analyze a single zipBoard article URL
	•	Batch analyze multiple URLs
	•	Show skipped (already processed) articles
	•	Display live processing status
	•	Embed live Google Sheet view

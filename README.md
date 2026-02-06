# zipBoard Documentation Intelligence

A deterministic, LLM-assisted system to audit zipBoard Help Center documentation, identify systemic documentation gaps, and produce a prioritized, evaluator-ready gap analysis for product improvement.

---

## 📌 Overview

**zipBoard Documentation Intelligence** analyzes zipBoard Help Center articles end-to-end to:

- Catalog documentation coverage
- Detect missing or unclear information (documentation gaps)
- Identify systemic gaps across multiple articles
- Prioritize gaps based on user impact
- Generate clear, business-justified rationale using LLMs
- Deliver results in spreadsheet-friendly, decision-ready format

The system is designed for **documentation audits**, **product teams**, and **evaluators**, with a strong emphasis on **traceability, determinism, and clarity**.

---

## 🎯 Objectives

- Improve user self-service and onboarding
- Reduce support dependency caused by unclear docs
- Identify high-impact documentation improvements
- Provide actionable insights instead of generic feedback

---

## 🧠 Key Features

### 1. Full Documentation Audit
- Scrapes all zipBoard Help Center articles
- Extracts clean, noise-free content
- Captures metadata such as category, content type, topics, and screenshots

### 2. Semantic Gap Detection
- Detects **missing sections users expect**, not missing steps
- Category-aware (API, Roles & Permissions, Integrations, etc.)
- Content-type-aware (How-to, Guide, Reference, Troubleshooting)
- Produces aggregation-ready, human-readable gaps

### 3. Systemic Gap Analysis
- Aggregates gaps across all articles
- Filters for **systemic gaps** (appearing in multiple articles)
- Assigns priority based on:
  - Frequency across articles
  - Severity of affected articles

### 4. LLM-Generated Rationale (Gemini)
- Explains *why* a gap matters
- Describes user friction or risk
- Justifies why fixing the gap improves self-service
- Controlled, bounded prompts (no hallucination)

### 5. Spreadsheet-First Output
- Google Sheets integration
- Two structured outputs:
  - **Article Audit Sheet**
  - **Gap Analysis Sheet**

---

## 🧩 Architecture Overview

zipBoard Help Center URLs
↓
Article Scraper
↓
Article Structurer (Semantic Layer)
↓
Processed Article Store (JSON)
↓
Gap Analysis Engine
↓
Google Sheets Output

---

## 🔄 Workflow Summary

### Step 1: Article Discovery & Scraping
- Discovers all Help Center articles via collections
- Fetches article HTML with timeout and retry safety
- Cleans content and removes HelpScout boilerplate

### Step 2: Article Structuring
Each article is converted into structured metadata:
- Category
- Content type
- Topics covered
- Per-article documentation gaps
- Severity and risk level

### Step 3: Processed Article Store
- Structured JSON files stored in `data/processed/`
- Enables re-running analysis without re-scraping
- Provides evaluator-friendly traceability

### Step 4: Gap Analysis Engine
- Aggregates gaps across articles
- Normalizes similar gaps
- Filters systemic gaps
- Calculates priority
- Generates rationale using Gemini
- Writes results to Gap Analysis sheet

---

## 📊 Outputs

### 1. Article Audit Sheet
One row per article, including:
- Metadata
- Detected gaps
- Severity
- Automation opportunity
- Risk level

### 2. Gap Analysis Sheet
Includes:
- Gap ID
- Category
- Gap description
- Priority
- Suggested article title
- LLM-generated rationale

Together, these sheets form a **documentation improvement roadmap**.

---

## 🛠️ Tech Stack

- **Python 3.11**
- **Streamlit** – UI & interaction
- **Requests + BeautifulSoup** – Web scraping
- **Google Sheets API** – Output delivery
- **Gemini (LLM)** – Rationale generation
- **HF Client** – Topic detection
- **JSON-based pipeline** – Deterministic processing


---

## ▶️ How to Run

### CLI Mode (Batch Audit)
```bash
python -m app.main

UI Mode (Streamlit)

streamlit run streamlit_app/app.py


⸻

🧪 Design Principles
	•	Deterministic before LLM
	•	LLM used only for reasoning and explanation
	•	No black-box decisions
	•	Re-runnable and traceable
	•	Spreadsheet-first delivery
	•	Evaluator-friendly outputs

⸻

📄 Workflow Documentation

Detailed workflow documentation is available in:
	•	workflow.md

This includes:
	•	System objectives
	•	Step-by-step workflow
	•	LLM prompt templates
	•	Design rationale
	•	PDF export instructions

⸻

🏁 Outcome

This system transforms unstructured help documentation into a prioritized, explainable, and actionable gap analysis, enabling zipBoard to systematically improve:
	•	User onboarding
	•	Role clarity
	•	API usability
	•	Integration reliability
	•	Overall self-service quality

⸻

👤 Author

Dinesh Kumar
GitHub: https://github.com/Dineshkumar0705

⸻

📜 License

For evaluation and demonstration purposes.

If you want, next I can:
- Tighten this for **submission reviewers**
- Add **screenshots section**
- Add **evaluation rubric mapping**
- Create a **1-page executive summary**

Just say the word 👍

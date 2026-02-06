import json
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Dict

from app.llm.gemini_client import GeminiClient


class GapAnalysisEngine:
    """
    Dedicated engine for GAP ANALYSIS SHEET.

    Reads processed article JSONs and produces
    a concise, evaluator-ready gap analysis.

    Design principles:
    - Rationale is NEVER empty
    - Short, impact-focused explanations
    - Gemini is enhancement, not dependency
    """

    def __init__(self, processed_dir: Path, sheet_manager):
        self.processed_dir = Path(processed_dir)
        self.sheet_manager = sheet_manager
        self.gemini = GeminiClient()

    # ==================================================
    # LOAD PROCESSED ARTICLES
    # ==================================================
    def _load_articles(self) -> List[Dict]:
        articles = []

        if not self.processed_dir.exists():
            return articles

        for path in self.processed_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    articles.append(data)
            except Exception:
                continue

        return articles

    # ==================================================
    # PRIORITY LOGIC
    # ==================================================
    def _calculate_priority(self, occurrences: List[Dict], total: int) -> str:
        freq = len(occurrences)
        severities = [o["severity"] for o in occurrences]

        ratio = freq / max(total, 1)

        if ratio >= 0.5 or severities.count("High") >= 3:
            return "High"
        if ratio >= 0.25 or severities.count("Medium") >= 2:
            return "Medium"
        return "Low"

    # ==================================================
    # ARTICLE TITLE SUGGESTION
    # ==================================================
    def _suggest_title(self, gap: str) -> str:
        clean = gap.replace("missing", "").strip()
        return f"Guide: {clean.capitalize()}"

    # ==================================================
    # BASELINE RATIONALE (ALWAYS USED)
    # ==================================================
    def _baseline_rationale(self, category: str, gap: str) -> str:
        """
        Deterministic, short, evaluator-friendly rationale.
        """

        if category == "API":
            return "Users need clear API documentation to build and maintain custom integrations."

        if category == "Integrations":
            return "Users lack clarity during integration setup, increasing failures and support dependency."

        if category == "Roles & Permissions":
            return "Users cannot clearly understand access boundaries, causing confusion for non-admin users."

        if category == "Troubleshooting":
            return "Without failure scenarios, users cannot self-diagnose issues effectively."

        return "Users lack critical guidance, reducing successful onboarding and self-service."

    # ==================================================
    # GEMINI RATIONALE (OPTIONAL ENHANCEMENT)
    # ==================================================
    def _generate_rationale(self, category: str, gap: str, priority: str) -> str:
        """
        Gemini-enhanced rationale.
        Must be SHORT and DIRECT.
        """

        prompt = f"""
Rewrite this rationale in one short sentence.

Category: {category}
Gap: {gap}

Focus only on user impact.
No explanations.
No filler.
"""

        try:
            result = self.gemini._run(prompt)

            if not result or not isinstance(result, str):
                raise ValueError("Invalid Gemini response")

            cleaned = result.strip()

            if len(cleaned) < 15 or len(cleaned) > 160:
                raise ValueError("Gemini response unsuitable")

            return cleaned

        except Exception:
            return self._baseline_rationale(category, gap)

    # ==================================================
    # MAIN PIPELINE
    # ==================================================
    def run(self, top_n: int = 5):
        print("🔥 GapAnalysisEngine RUNNING")

        articles = self._load_articles()
        if not articles:
            print("⚠️ No processed articles found")
            return

        total_articles = len(articles)
        gap_map = defaultdict(list)

        # ----------------------------------------------
        # COLLECT + NORMALIZE GAPS
        # ----------------------------------------------
        for article in articles:
            category = article.get("category", "General")
            severity = article.get("gap_severity", "Low")
            gaps = article.get("gaps_identified", [])

            if not isinstance(gaps, list):
                continue

            for gap in gaps:
                if not isinstance(gap, str):
                    continue

                normalized = gap.strip().lower()
                if not normalized:
                    continue

                gap_map[normalized].append({
                    "category": category,
                    "severity": severity
                })

        if not gap_map:
            print("⚠️ No gaps detected")
            return

        # ----------------------------------------------
        # SYSTEMIC GAPS (>= 2 ARTICLES)
        # ----------------------------------------------
        systemic_gaps = {
            gap: occ for gap, occ in gap_map.items() if len(occ) >= 2
        }

        if not systemic_gaps:
            print("⚠️ No systemic gaps found")
            return

        # ----------------------------------------------
        # SORT BY IMPACT
        # ----------------------------------------------
        sorted_gaps = sorted(
            systemic_gaps.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )

        gap_rows = []

        for idx, (gap, occurrences) in enumerate(sorted_gaps[:top_n], start=1):
            categories = [o["category"] for o in occurrences]
            dominant_category = Counter(categories).most_common(1)[0][0]

            priority = self._calculate_priority(
                occurrences,
                total_articles
            )

            rationale = self._generate_rationale(
                dominant_category,
                gap,
                priority
            )

            gap_rows.append({
                "gap_id": f"GAP-{idx:03d}",
                "category": dominant_category,
                "gap_description": gap,
                "priority": priority,
                "suggested_article_title": self._suggest_title(gap),
                "rationale": rationale
            })

        # ----------------------------------------------
        # WRITE TO SHEET
        # ----------------------------------------------
        print("📤 Writing Gap Analysis sheet...")
        self.sheet_manager.upsert_gap_analysis(gap_rows)
        print(f"✅ Gap Analysis updated ({len(gap_rows)} gaps)")
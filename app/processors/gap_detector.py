import json
from collections import defaultdict, Counter
from pathlib import Path
from typing import List, Dict


class GapDetector:
    """
    Aggregates documentation gaps across processed articles
    and produces a prioritized, deduplicated gap analysis.
    """

    def __init__(self, processed_dir: str = "data/processed"):
        self.processed_dir = Path(processed_dir)

    # --------------------------------------------------
    # Load processed articles
    # --------------------------------------------------
    def load_articles(self) -> List[Dict]:
        """
        Loads all processed article JSON files safely.
        """
        articles = []

        if not self.processed_dir.exists():
            return articles

        for file_path in self.processed_dir.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        articles.append(data)
            except Exception as e:
                print(f"⚠️ Failed to read {file_path.name}: {e}")

        return articles

    # --------------------------------------------------
    # Normalize gap descriptions
    # --------------------------------------------------
    def _normalize_gap(self, gap: str) -> str:
        """
        Normalizes gap text to improve aggregation.
        """
        gap = gap.lower().strip()

        replacements = {
            "explain": "",
            "missing": "",
            "include": "",
            "mention": "",
        }

        for k, v in replacements.items():
            gap = gap.replace(k, "")

        return " ".join(gap.split())

    # --------------------------------------------------
    # Detect and aggregate gaps
    # --------------------------------------------------
    def detect_gaps(self, top_n: int = 5) -> List[Dict]:
        """
        Aggregates gaps across all articles and returns
        the top N most impactful gaps.
        """

        articles = self.load_articles()
        if not articles:
            return []

        # normalized_gap -> list of occurrences
        gap_counter = defaultdict(list)

        for article in articles:
            article_id = article.get("article_id", "UNKNOWN")
            category = article.get("category", "General")
            severity = article.get("gap_severity", "Low")
            gaps = article.get("gaps_identified", [])

            if not isinstance(gaps, list):
                continue

            for gap in gaps:
                if not isinstance(gap, str) or not gap.strip():
                    continue

                normalized = self._normalize_gap(gap)

                gap_counter[normalized].append({
                    "article_id": article_id,
                    "category": category,
                    "severity": severity
                })

        # --------------------------------------------------
        # Prioritize gaps
        # --------------------------------------------------
        sorted_gaps = sorted(
            gap_counter.items(),
            key=lambda item: len(item[1]),
            reverse=True
        )

        gap_analysis = []

        for idx, (gap_desc, occurrences) in enumerate(sorted_gaps[:top_n], start=1):
            severities = [o["severity"] for o in occurrences]
            categories = [o["category"] for o in occurrences]

            # Priority logic
            if severities.count("High") >= 2:
                priority = "High"
            elif severities.count("Medium") >= 1:
                priority = "Medium"
            else:
                priority = "Low"

            # Most common category
            dominant_category = Counter(categories).most_common(1)[0][0]

            gap_analysis.append({
                "gap_id": f"GAP-{idx:03d}",
                "category": dominant_category,
                "gap_description": gap_desc,
                "priority": priority,
                "suggested_article_title": f"Guide: {gap_desc.title()}",
                "rationale": f"Identified in {len(occurrences)} articles"
            })

        return gap_analysis
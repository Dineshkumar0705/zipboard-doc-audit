from app.llm.hf_client import HFClient


class ArticleJSONStructurer:
    """
    Converts raw scraped article into structured documentation metadata.

    Gap detection philosophy:
    - Semantic, not checklist-based
    - Category + content-type aware
    - Produces clean, aggregation-ready gaps
    """

    def __init__(self):
        self.hf = HFClient()

        self.TOPICS = [
            "onboarding",
            "roles and permissions",
            "collaboration",
            "projects",
            "integrations",
            "api",
            "troubleshooting",
            "billing",
            "security"
        ]

    # ==================================================
    # MAIN STRUCTURING
    # ==================================================
    def structure_article(self, article: dict) -> dict:
        text = (article.get("raw_text") or "")[:3000]
        title = article.get("title", "") or ""

        category = self._infer_category_heuristic(title, text)
        content_type = self._infer_content_type_heuristic(text)
        topics = self._infer_topics(text)

        raw_gaps = self._infer_semantic_gaps(
            text=text,
            category=category,
            content_type=content_type
        )

        # 🔑 CANONICALIZE GAPS (CRITICAL FIX)
        gaps = [self._canonicalize_gap(g) for g in raw_gaps]

        # Remove duplicates while preserving order
        gaps = list(dict.fromkeys(gaps))

        # Severity is impact-based
        if len(gaps) >= 2:
            severity = "High"
        elif gaps:
            severity = "Medium"
        else:
            severity = "Low"

        return {
            "article_id": article.get("article_id"),
            "article_title": title,
            "category": category,
            "section": "Knowledge Base",
            "url": article.get("url"),
            "content_type": content_type,
            "approx_word_count": len(text.split()),
            "has_screenshots": article.get("has_images", False),
            "topics_covered": topics,
            "gaps_identified": gaps,
            "target_user_role": "Mixed",
            "onboarding_stage": "First-time setup",
            "gap_severity": severity,
            "automation_opportunity": "Yes" if gaps else "No",
            "category_risk_level": severity
        }

    # ==================================================
    # GAP CANONICALIZATION (NEW – DO NOT REMOVE)
    # ==================================================
    def _canonicalize_gap(self, gap: str) -> str:
        """
        Converts semantically similar gap phrasings
        into a single canonical form for aggregation.
        """
        g = gap.lower().strip()

        if any(k in g for k in ["example", "workflow", "use case"]):
            return "missing practical examples or end-to-end user workflows"

        if any(k in g for k in ["error", "fail", "failure", "troubleshoot"]):
            return "missing guidance on error scenarios and failure handling"

        if any(k in g for k in ["role", "permission", "access"]):
            return "missing explanation of roles, permissions, and access levels"

        if any(k in g for k in ["limit", "constraint", "restriction", "boundary"]):
            return "missing documented limitations and usage constraints"

        return g

    # ==================================================
    # TOPICS
    # ==================================================
    def _infer_topics(self, text: str) -> list:
        primary = self.hf.detect_topics(
            text=text,
            allowed_topics=self.TOPICS,
            threshold=0.25,
            max_topics=3
        )

        specific = self._extract_specific_topics(text)
        topics = list(dict.fromkeys(primary + specific))

        return topics[:5] if topics else ["onboarding"]

    # ==================================================
    # SEMANTIC GAP DETECTION
    # ==================================================
    def _infer_semantic_gaps(
        self,
        text: str,
        category: str,
        content_type: str,
        max_gaps: int = 3
    ) -> list:
        """
        Detects missing SECTIONS users expect.
        """

        t = text.lower()
        gaps = []

        # ---- Roles / Access ----
        if category in {"Roles & Permissions", "Integrations", "API"}:
            if not any(k in t for k in ["role", "permission", "access"]):
                gaps.append(
                    "does not clearly explain required roles, permissions, or access levels"
                )

        # ---- Error handling ----
        if category in {"Integrations", "API", "Troubleshooting"}:
            if not any(k in t for k in ["error", "fail", "issue", "troubleshoot"]):
                gaps.append(
                    "missing guidance on error scenarios and failure handling"
                )

        # ---- Constraints ----
        if category in {"API", "Integrations"}:
            if not any(k in t for k in ["limit", "only", "cannot", "restriction"]):
                gaps.append(
                    "no documented limitations, constraints, or usage boundaries"
                )

        # ---- Examples ----
        if content_type in {"How-to", "Guide"}:
            if not any(k in t for k in ["example", "workflow", "use case"]):
                gaps.append(
                    "lacks practical examples or end-to-end user workflows"
                )

        return gaps[:max_gaps]

    # ==================================================
    # SPECIFIC TOPICS
    # ==================================================
    def _extract_specific_topics(self, text: str, max_items: int = 5) -> list:
        keywords = [
            "manager", "collaborator", "client", "project",
            "organization", "permission", "role", "api",
            "token", "integration", "jira", "webhook",
            "review", "task"
        ]

        text = text.lower()
        found = [k for k in keywords if k in text]
        return list(dict.fromkeys(found))[:max_items]

    # ==================================================
    # CATEGORY
    # ==================================================
    def _infer_category_heuristic(self, title: str, text: str) -> str:
        t = f"{title} {text}".lower()

        if "api" in t:
            return "API"
        if "integration" in t:
            return "Integrations"
        if any(k in t for k in ["role", "manager", "collaborator", "client"]):
            return "Roles & Permissions"
        if "project" in t or "phase" in t:
            return "Projects & Phases"
        if "error" in t or "issue" in t:
            return "Troubleshooting"
        if "account" in t or "billing" in t:
            return "Account & Management"

        return "General"

    # ==================================================
    # CONTENT TYPE
    # ==================================================
    def _infer_content_type_heuristic(self, text: str) -> str:
        t = text.lower()

        if "step" in t or "follow these" in t or "how to" in t:
            return "How-to"
        if "faq" in t:
            return "FAQ"
        if "error" in t or "issue" in t:
            return "Troubleshooting"
        if "reference" in t:
            return "Reference"

        return "Guide"
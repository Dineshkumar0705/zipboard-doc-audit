from app.llm.hf_client import HFClient


class ArticleJSONStructurer:
    """
    Converts raw scraped article into structured documentation metadata.

    AI usage (Hugging Face only):
    - Topics covered (zero-shot, multi-label)
    - Gap detection (question answering, max 3)

    Design goals:
    - Quota-safe
    - Deterministic
    - Never stuck / never empty
    - Human-readable + machine-consistent output
    """

    def __init__(self):
        self.hf = HFClient()

        # --------------------------------------------------
        # Controlled vocabularies (PRIMARY semantic topics)
        # --------------------------------------------------
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

        # 🔥 Reduced to 3 → big performance win
        self.GAP_QUESTIONS = [
            "Does this article explain prerequisites?",
            "Does this article explain common errors?",
            "Does this article explain limitations?"
        ]

    # ==================================================
    # MAIN STRUCTURING
    # ==================================================
    def structure_article(self, article: dict) -> dict:
        # 🔒 Hard trim → prevents HF freeze
        text = (article.get("raw_text") or "")[:3000]
        title = article.get("title", "") or ""

        # -------- CATEGORY (heuristic, zero cost) --------
        category = self._infer_category_heuristic(title, text)

        # -------- CONTENT TYPE (heuristic, zero cost) --------
        content_type = self._infer_content_type_heuristic(text)

        # -------- TOPICS (semantic + specific) --------
        topics = self._infer_topics(text)

        # -------- GAPS (HF QA, MAX 3) --------
        gaps = self.hf.detect_gaps(
            text=text,
            questions=self.GAP_QUESTIONS,
            score_threshold=0.25,
            max_gaps=3
        )

        # -------- SEVERITY --------
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
    # TOPIC INFERENCE (HF + SPECIFIC KEYWORDS)
    # ==================================================
    def _infer_topics(self, text: str) -> list:
        """
        Layered topic detection:
        1. HF zero-shot (controlled semantic topics)
        2. Deterministic keyword extraction (specific topics)
        3. Guaranteed non-empty
        """

        # ---- Layer 1: Semantic topics (HF) ----
        primary_topics = self.hf.detect_topics(
            text=text,
            allowed_topics=self.TOPICS,
            threshold=0.25,   # raised → cleaner + faster
            max_topics=3
        )

        # ---- Layer 2: Specific topics (rule-based) ----
        specific_topics = self._extract_specific_topics(text)

        # ---- Merge (dedupe, preserve order) ----
        topics = list(dict.fromkeys(primary_topics + specific_topics))

        if topics:
            return topics[:5]

        # ---- Hard fallback (never empty) ----
        return ["onboarding"]

    # ==================================================
    # SPECIFIC TOPIC EXTRACTION (DETERMINISTIC)
    # ==================================================
    def _extract_specific_topics(self, text: str, max_items: int = 5) -> list:
        """
        Extracts fine-grained topics from article text.
        No LLM. No hallucination. Fast.
        """

        keywords = [
            "manager",
            "collaborator",
            "client",
            "project",
            "organization",
            "permission",
            "role",
            "api",
            "token",
            "integration",
            "jira",
            "webhook",
            "review",
            "task"
        ]

        text = text.lower()
        found = []

        for k in keywords:
            if k in text:
                found.append(k)

        return list(dict.fromkeys(found))[:max_items]

    # ==================================================
    # CATEGORY HEURISTICS (ZERO COST)
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
    # CONTENT TYPE HEURISTICS (ZERO COST)
    # ==================================================
    def _infer_content_type_heuristic(self, text: str) -> str:
        t = text.lower()

        if "step" in t or "follow these" in t or "how to" in t:
            return "How-to"
        if "frequently asked" in t or "faq" in t:
            return "FAQ"
        if "error" in t or "issue" in t:
            return "Troubleshooting"
        if "reference" in t:
            return "Reference"

        return "Guide"
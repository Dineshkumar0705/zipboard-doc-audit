import json
import re
from google import genai
from app.config import GEMINI_API_KEY


class GeminiClient:
    """
    Gemini client for SEMANTIC understanding of documentation.

    Uses Gemini ONLY for:
    - Category inference
    - Topics covered inference
    - Content type classification
    - Gap identification (MAX 5)

    Safe, deterministic, and interview-ready.
    """

    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY not set in .env")

        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.model = "models/gemini-pro-latest"

        # Controlled vocabularies
        self.allowed_categories = [
            "Getting Started",
            "Roles & Permissions",
            "Collaboration",
            "Projects & Phases",
            "Integrations",
            "API",
            "Troubleshooting",
            "Account & Management",
            "Security",
            "General"
        ]

        self.allowed_topics = [
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

        self.allowed_content_types = [
            "How-to",
            "Guide",
            "FAQ",
            "Reference",
            "Troubleshooting"
        ]

    # ==================================================
    # MAIN ANALYSIS ENTRYPOINT
    # ==================================================
    def analyze_article(self, article_text: str) -> dict:
        """
        Input: full raw article text
        Output (guaranteed schema):
        {
            category: str,
            topics_covered: list[str],
            content_type: str,
            gaps_identified: list[str]
        }
        """

        if not article_text:
            return self._fallback()

        prompt = f"""
You are an expert documentation analyst.

Analyze the following help article and return STRICT JSON.

ALLOWED CATEGORY VALUES:
{", ".join(self.allowed_categories)}

ALLOWED TOPICS:
{", ".join(self.allowed_topics)}

ALLOWED CONTENT TYPES:
{", ".join(self.allowed_content_types)}

TASKS:
1. Choose ONE best Category.
2. Identify up to 5 Topics Covered (from allowed list).
3. Choose ONE Content Type.
4. Identify up to 5 IMPORTANT documentation gaps.

RULES:
- Use ONLY allowed values.
- MAX 5 topics, MAX 5 gaps.
- Short phrases only.
- Return VALID JSON ONLY.
- No explanations.
- No markdown.

ARTICLE:
\"\"\"
{article_text[:5000]}
\"\"\"

JSON FORMAT:
{{
  "category": "",
  "topics_covered": [],
  "content_type": "",
  "gaps_identified": []
}}
"""

        raw_response = self._run(prompt)
        return self._safe_parse(raw_response)

    # ==================================================
    # SAFE JSON PARSER
    # ==================================================
    def _safe_parse(self, text: str) -> dict:
        """
        Extracts and validates JSON from Gemini output.
        Never crashes the pipeline.
        """

        try:
            # Remove markdown/code blocks if any
            cleaned = re.sub(r"```.*?```", "", text, flags=re.S)
            match = re.search(r"\{.*\}", cleaned, flags=re.S)

            if not match:
                return self._fallback()

            data = json.loads(match.group())

        except Exception:
            return self._fallback()

        # -------- CATEGORY --------
        category = data.get("category")
        if category not in self.allowed_categories:
            category = "General"

        # -------- TOPICS --------
        topics = []
        for t in data.get("topics_covered", []):
            t = t.lower()
            if t in self.allowed_topics and t not in topics:
                topics.append(t)
            if len(topics) == 5:
                break

        # -------- CONTENT TYPE --------
        content_type = data.get("content_type")
        if content_type not in self.allowed_content_types:
            content_type = "How-to"

        # -------- GAPS --------
        gaps = []
        for g in data.get("gaps_identified", []):
            if isinstance(g, str) and g.strip():
                gaps.append(g.strip().lower())
            if len(gaps) == 5:
                break

        return {
            "category": category,
            "topics_covered": topics,
            "content_type": content_type,
            "gaps_identified": gaps
        }

    # ==================================================
    # FALLBACK
    # ==================================================
    def _fallback(self) -> dict:
        return {
            "category": "General",
            "topics_covered": [],
            "content_type": "How-to",
            "gaps_identified": []
        }

    # ==================================================
    # INTERNAL RUNNER
    # ==================================================
    def _run(self, prompt: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
            return response.text or ""
        except Exception:
            return ""
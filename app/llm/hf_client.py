import time
from huggingface_hub import InferenceClient
from app.config import HF_API_TOKEN


class HFClient:
    """
    Hugging Face client for lightweight semantic signals.

    Used for:
    - Topic detection (zero-shot, multi-label)

    Optional use:
    - Shallow gap hints (QA) — NOT primary gap logic

    Guarantees:
    - Free-tier safe
    - Truncated input (prevents hangs)
    - Visible progress logs
    - Never crashes pipeline
    """

    def __init__(self):
        if not HF_API_TOKEN:
            raise ValueError("HF_API_TOKEN not found in .env")

        self.client = InferenceClient(token=HF_API_TOKEN)

        # Free-tier friendly models
        self.ZERO_SHOT_MODEL = "typeform/distilbert-base-uncased-mnli"
        self.QA_MODEL = "deepset/roberta-base-squad2"

        # HARD SAFETY LIMIT
        self.MAX_INPUT_CHARS = 2000

    # ==================================================
    # TOPIC DETECTION (PRIMARY HF USAGE)
    # ==================================================
    def detect_topics(
        self,
        text: str,
        allowed_topics: list,
        threshold: float = 0.2,
        max_topics: int = 5
    ) -> list:
        """
        Detects high-level semantic topics.

        Guarantees:
        - Never blocks
        - Never crashes
        - Never returns empty if labels exist
        """

        if not text or not allowed_topics:
            return []

        safe_text = text[: self.MAX_INPUT_CHARS]

        print("      🔍 HF: topic detection started", flush=True)
        start = time.time()

        try:
            result = self.client.zero_shot_classification(
                safe_text,
                allowed_topics,
                model=self.ZERO_SHOT_MODEL
            )
        except Exception as e:
            print("      ⚠️ HF topic detection failed:", e, flush=True)
            return []

        print(
            f"      ✅ HF: topic detection finished "
            f"({time.time() - start:.1f}s)",
            flush=True
        )

        # Normalize HF output
        if isinstance(result, list):
            result = result[0] if result else {}

        labels = result.get("labels", [])
        scores = result.get("scores", [])

        topics = []
        for label, score in zip(labels, scores):
            if score >= threshold and label not in topics:
                topics.append(label)
            if len(topics) == max_topics:
                break

        # HARD FALLBACK
        if not topics and labels:
            topics = [labels[0]]

        return topics

    # ==================================================
    # GAP QA (OPTIONAL / FALLBACK ONLY)
    # ==================================================
    def detect_gaps(
        self,
        text: str,
        questions: list,
        score_threshold: float = 0.25,
        max_gaps: int = 3
    ) -> list:
        """
        Lightweight QA-based gap hints.

        ⚠️ NOT primary gap detection.
        Gemini handles semantic gaps.
        """

        if not text or not questions:
            return []

        safe_text = text[: self.MAX_INPUT_CHARS]
        gaps = []

        for idx, q in enumerate(questions, start=1):
            print(f"      ❓ HF QA {idx}/{len(questions)}", flush=True)

            try:
                result = self.client.question_answering(
                    question=q,
                    context=safe_text,
                    model=self.QA_MODEL
                )
            except Exception as e:
                print("      ⚠️ HF QA failed:", e, flush=True)
                continue

            score = float(result.get("score", 0.0))

            if score < score_threshold:
                gap = (
                    q.replace("Does this article", "")
                     .replace("?", "")
                     .strip()
                     .lower()
                )
                gaps.append(gap)

            if len(gaps) == max_gaps:
                break

        return gaps
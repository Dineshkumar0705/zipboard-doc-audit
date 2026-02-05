import re

def clean_text(text: str) -> str:
    """
    Cleans excessive whitespace and junk characters
    """
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()
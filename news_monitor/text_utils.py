import re
import unicodedata
from html import unescape


WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    text = unescape(value or "")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    return WHITESPACE_RE.sub(" ", text).strip()


def compact_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", unescape(value or "")).strip()

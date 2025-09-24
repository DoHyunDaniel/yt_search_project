import html
import re
from typing import Tuple

_whitespace_re = re.compile(r"\s+")
_emoji_re = re.compile(
    r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+",
    flags=re.UNICODE,
)


def clean_text(raw: str) -> str:
    if not raw:
        return ""
    text = html.unescape(raw)
    text = _emoji_re.sub(" ", text)
    text = _whitespace_re.sub(" ", text)
    return text.strip()


def label_to_score(label: str, prob: float) -> float:
    # Map label to signed score (-1 ~ 1)
    if label == "pos":
        return max(min(prob, 1.0), 0.0)
    if label == "neg":
        return -max(min(prob, 1.0), 0.0)
    return 0.0



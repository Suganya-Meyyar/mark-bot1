from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from rapidfuzz import fuzz, process


@dataclass(frozen=True)
class Intent:
    kind: str  # "subject_mark" | "all_marks" | "unknown"
    subject: Optional[str] = None


def _clean(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s\-\_]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def infer_intent(user_text: str, subjects: list[str]) -> Intent:
    t = _clean(user_text)
    if not t:
        return Intent(kind="unknown")

    # If user asks for all marks
    if any(p in t for p in ["all marks", "show my marks", "my marks", "marks list", "all subjects", "overall marks"]):
        return Intent(kind="all_marks")

    # Subject-specific mark query (default)
    if not subjects:
        return Intent(kind="subject_mark", subject=None)

    # Fuzzy match subject against the question
    # Use partial_ratio because users say "my mark in ds"
    best = process.extractOne(
        t,
        subjects,
        scorer=fuzz.partial_ratio,
    )
    if not best:
        return Intent(kind="subject_mark", subject=None)

    subject, score, _ = best
    # Require a reasonable match quality
    if score < 65:
        return Intent(kind="subject_mark", subject=None)

    return Intent(kind="subject_mark", subject=subject)


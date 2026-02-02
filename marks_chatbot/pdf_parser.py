from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Iterable, Optional

import pandas as pd
import pdfplumber

from .db import MarkRow


@dataclass(frozen=True)
class ParseResult:
    rows: list[MarkRow]
    warnings: list[str]


_HEADER_ALIASES = {
    "student_id": {"student_id", "student id", "roll", "rollno", "roll no", "roll_no", "register", "reg no"},
    "student_name": {"student_name", "student name", "name"},
    "subject": {"subject", "course", "paper", "sub"},
    "mark": {"mark", "marks", "score", "total"},
}


def _norm(s: str) -> str:
    return re.sub(r"[\s\-_]+", " ", str(s).strip().lower())


def _best_header_map(cols: Iterable[str]) -> dict[str, str]:
    cols = list(cols)
    norm_to_orig = {_norm(c): c for c in cols}
    found: dict[str, str] = {}
    for canonical, aliases in _HEADER_ALIASES.items():
        for alias in aliases:
            alias_n = _norm(alias)
            if alias_n in norm_to_orig:
                found[canonical] = norm_to_orig[alias_n]
                break
    return found


def _try_parse_mark(v: object) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    s = s.replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def parse_marks_pdf(pdf_bytes: bytes, source_file: str) -> ParseResult:
    warnings: list[str] = []
    tables: list[pd.DataFrame] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_idx, page in enumerate(pdf.pages):
            try:
                extracted = page.extract_table()
            except Exception:
                extracted = None

            if extracted:
                df = pd.DataFrame(extracted[1:], columns=extracted[0])
                df = df.dropna(how="all")
                if not df.empty:
                    tables.append(df)
            else:
                # Fallback: try to find multiple tables on the page
                try:
                    extracted_tables = page.extract_tables() or []
                except Exception:
                    extracted_tables = []
                for t in extracted_tables:
                    if not t or len(t) < 2:
                        continue
                    df = pd.DataFrame(t[1:], columns=t[0])
                    df = df.dropna(how="all")
                    if not df.empty:
                        tables.append(df)

            if page_idx == 0 and not tables:
                warnings.append(
                    "No table detected on page 1. Ensure the PDF contains a clear table with headers."
                )

    if not tables:
        return ParseResult(rows=[], warnings=warnings or ["No readable tables found in the PDF."])

    # Choose the table that looks most like a marks table
    scored: list[tuple[int, pd.DataFrame, dict[str, str]]] = []
    for df in tables:
        header_map = _best_header_map(df.columns)
        score = sum(1 for k in ("student_id", "subject", "mark") if k in header_map)
        scored.append((score, df, header_map))
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_df, header_map = scored[0]

    if best_score < 3:
        warnings.append(
            "Could not confidently match PDF headers to required columns. "
            "Expected columns similar to: student_id, subject, mark."
        )

    rows: list[MarkRow] = []
    sid_col = header_map.get("student_id")
    sub_col = header_map.get("subject")
    mark_col = header_map.get("mark")
    name_col = header_map.get("student_name")

    if not (sid_col and sub_col and mark_col):
        return ParseResult(rows=[], warnings=warnings)

    for _, r in best_df.iterrows():
        student_id = str(r.get(sid_col, "")).strip()
        subject = str(r.get(sub_col, "")).strip()
        mark = _try_parse_mark(r.get(mark_col))
        student_name = None
        if name_col:
            student_name = str(r.get(name_col, "")).strip() or None

        if not student_id or not subject or mark is None:
            continue

        rows.append(
            MarkRow(
                student_id=student_id,
                student_name=student_name,
                subject=subject,
                mark=mark,
                source_file=source_file,
            )
        )

    if not rows:
        warnings.append("Parsed 0 valid rows. Check that student_id/subject/mark values are filled.")

    return ParseResult(rows=rows, warnings=warnings)


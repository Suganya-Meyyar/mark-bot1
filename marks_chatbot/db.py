from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class MarkRow:
    student_id: str
    student_name: Optional[str]
    subject: str
    mark: float
    source_file: str


def get_db_path() -> Path:
    data_dir = Path.cwd() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "marks.sqlite3"


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(get_db_path().as_posix())
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with connect() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS marks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              student_id TEXT NOT NULL,
              student_name TEXT,
              subject TEXT NOT NULL,
              mark REAL NOT NULL,
              source_file TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        con.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_marks_student_subject
            ON marks(student_id, subject);
            """
        )


def insert_marks(rows: Iterable[MarkRow]) -> int:
    rows = list(rows)
    if not rows:
        return 0
    with connect() as con:
        con.executemany(
            """
            INSERT INTO marks (student_id, student_name, subject, mark, source_file)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (r.student_id.strip(), (r.student_name or None), r.subject.strip(), float(r.mark), r.source_file)
                for r in rows
            ],
        )
        return len(rows)


def list_subjects() -> list[str]:
    with connect() as con:
        cur = con.execute("SELECT DISTINCT subject FROM marks ORDER BY subject COLLATE NOCASE")
        return [r["subject"] for r in cur.fetchall()]


def get_student_name(student_id: str) -> Optional[str]:
    with connect() as con:
        cur = con.execute(
            "SELECT student_name FROM marks WHERE student_id = ? AND student_name IS NOT NULL LIMIT 1",
            (student_id.strip(),),
        )
        row = cur.fetchone()
        return None if row is None else row["student_name"]


def get_mark(student_id: str, subject: str) -> Optional[float]:
    with connect() as con:
        cur = con.execute(
            """
            SELECT mark
            FROM marks
            WHERE student_id = ? AND subject = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (student_id.strip(), subject.strip()),
        )
        row = cur.fetchone()
        return None if row is None else float(row["mark"])


def get_all_marks(student_id: str) -> list[tuple[str, float]]:
    with connect() as con:
        cur = con.execute(
            """
            SELECT subject, mark
            FROM marks
            WHERE student_id = ?
            ORDER BY subject COLLATE NOCASE
            """,
            (student_id.strip(),),
        )
        return [(r["subject"], float(r["mark"])) for r in cur.fetchall()]


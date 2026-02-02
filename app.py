from __future__ import annotations

import os
from datetime import datetime

import streamlit as st

from marks_chatbot.db import get_all_marks, get_mark, get_student_name, init_db, insert_marks, list_subjects
from marks_chatbot.nlp import infer_intent
from marks_chatbot.pdf_parser import parse_marks_pdf


def _staff_password_ok() -> bool:
    expected = os.getenv("STAFF_PASSWORD", "staff123")
    entered = st.session_state.get("staff_password", "")
    return bool(expected) and entered == expected


def _human_mark_reply(student_id: str, student_name: str | None, subject: str, mark: float) -> str:
    who = f"{student_name} ({student_id})" if student_name else student_id
    return f"Hi {who}! Your mark in **{subject}** is **{mark:g}**."


def _human_all_marks_reply(student_id: str, student_name: str | None, items: list[tuple[str, float]]) -> str:
    who = f"{student_name} ({student_id})" if student_name else student_id
    if not items:
        return f"I couldn't find any marks saved for **{who}** yet."
    lines = [f"Here are your saved marks, **{who}**:"]
    for subject, mark in items:
        lines.append(f"- **{subject}**: {mark:g}")
    return "\n".join(lines)


def main() -> None:
    st.set_page_config(page_title="Marks Chatbot (PDF Upload)", page_icon="📄", layout="centered")
    init_db()

    st.title("Student Marks Chatbot")
    st.caption("Staff uploads PDF → data saved → students ask in natural text.")

    tab_staff, tab_student = st.tabs(["Staff (Upload PDF)", "Student (Ask)"])

    with tab_staff:
        st.subheader("Staff upload")
        st.write("Upload a marks PDF that contains a table with columns like: student_id, subject, mark.")

        st.text_input("Staff password", type="password", key="staff_password")
        if not _staff_password_ok():
            st.info("Enter the staff password to enable upload.")
        else:
            uploaded = st.file_uploader("Upload marks PDF", type=["pdf"])
            if uploaded is not None:
                source_name = uploaded.name or f"upload-{datetime.now().isoformat()}.pdf"
                pdf_bytes = uploaded.getvalue()

                parsed = parse_marks_pdf(pdf_bytes=pdf_bytes, source_file=source_name)
                if parsed.warnings:
                    for w in parsed.warnings:
                        st.warning(w)

                st.write(f"Detected **{len(parsed.rows)}** mark rows.")
                if st.button("Save to database", type="primary", disabled=(len(parsed.rows) == 0)):
                    n = insert_marks(parsed.rows)
                    st.success(f"Saved {n} rows from `{source_name}`.")

    with tab_student:
        st.subheader("Ask about your marks")
        student_id = st.text_input("Student ID / Roll No", placeholder="e.g., 21CS045")
        question = st.text_input("Ask a question", placeholder='e.g., "my mark in ds" or "show my marks"')

        if st.button("Ask", type="primary", disabled=not (student_id.strip() and question.strip())):
            subjects = list_subjects()
            intent = infer_intent(question, subjects=subjects)
            name = get_student_name(student_id)

            if intent.kind == "all_marks":
                items = get_all_marks(student_id)
                st.markdown(_human_all_marks_reply(student_id, name, items))
            elif intent.kind == "subject_mark":
                if not intent.subject:
                    if subjects:
                        st.info("I couldn't detect the subject. Try: 'my mark in Data Structures'.")
                        st.caption("Available subjects: " + ", ".join(subjects[:30]) + (" ..." if len(subjects) > 30 else ""))
                    else:
                        st.info("No subjects found yet. Ask staff to upload the marks PDF first.")
                    st.stop()

                mark = get_mark(student_id, intent.subject)
                if mark is None:
                    st.info(f"I couldn't find a mark for **{intent.subject}** under student id **{student_id}**.")
                else:
                    st.markdown(_human_mark_reply(student_id, name, intent.subject, mark))
            else:
                st.info("Try asking: 'my mark in DS' or 'show my marks'.")


if __name__ == "__main__":
    main()


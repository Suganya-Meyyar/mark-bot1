from __future__ import annotations

import os
from datetime import datetime

import streamlit as st

from marks_chatbot.db import get_all_marks, get_mark, get_student_name, init_db, insert_marks, list_subjects
from marks_chatbot.nlp import infer_intent
from marks_chatbot.pdf_parser import parse_marks_pdf


# Simple demo student credentials.
# KEY = student_id / roll number exactly as in the marks PDF.
# VALUE = password for that student.
# Edit / extend this mapping for your real students.
STUDENT_PASSWORDS: dict[str, str] = {
    # Examples (replace with your own):
    # "21CS001": "pass001",
    # "21CS002": "pass002",
    "8649": "mzcet@123",
    "8888": "intel@123",
    "8650": "stefeena",
}

# Simple demo staff credentials.
# KEY = staff_id / username, VALUE = password.
STAFF_USERS: dict[str, str] = {
    # Examples (replace with your own):
    # "staff1": "staffpass",
    "10001": "staff@123",
}


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


def _answer_question_ui(student_id: str, question: str) -> None:
    student_id = student_id.strip()
    question = question.strip()
    if not student_id or not question:
        st.info("Please enter both Student ID and a question.")
        return

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
                st.caption(
                    "Available subjects: "
                    + ", ".join(subjects[:30])
                    + (" ..." if len(subjects) > 30 else "")
                )
            else:
                st.info("No subjects found yet. Ask staff to upload the marks PDF first.")
            return

        mark = get_mark(student_id, intent.subject)
        if mark is None:
            st.info(f"I couldn't find a mark for **{intent.subject}** under student id **{student_id}**.")
        else:
            st.markdown(_human_mark_reply(student_id, name, intent.subject, mark))
    else:
        st.info("Try asking: 'my mark in DS' or 'show my marks'.")


def _show_staff_gui() -> None:
    st.header("Staff dashboard")

    st.markdown("### Upload marks PDF")
    st.write("Upload a marks PDF that contains a table with columns like: student_id, subject, mark.")

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

    st.markdown("---")
    st.markdown("### Check a student's marks")
    staff_sid = st.text_input(
        "Student ID / Roll No (for lookup)",
        placeholder="e.g., 21CS045",
        key="staff_lookup_sid",
    )
    staff_q = st.text_area(
        "Ask about this student's marks",
        placeholder='e.g., "what is this student mark in ds" or "show this student marks"',
        key="staff_lookup_q",
    )
    if st.button(
        "Ask as staff",
        type="secondary",
        disabled=not (staff_sid.strip() and staff_q.strip()),
    ):
        _answer_question_ui(staff_sid, staff_q)


def _show_student_gui() -> None:
    st.header("Student dashboard")

    # Student ID comes from login and cannot be changed here
    student_id = st.session_state.get("student_id", "")
    st.text_input(
        "Your Student ID / Roll No",
        value=student_id,
        disabled=True,
    )

    st.markdown("### Ask about your marks")
    question = st.text_input(
        "Ask a question",
        placeholder='e.g., "my mark in ds" or "show my marks"',
        key="student_question",
    )

    if st.button("Ask", type="primary", disabled=not (student_id.strip() and question.strip())):
        _answer_question_ui(student_id, question)


def main() -> None:
    st.set_page_config(page_title="Marks Chatbot (PDF Upload)", page_icon="📄", layout="centered")
    init_db()

    # Simple "navigation": first show login page, then show GUI based on chosen role.
    if "role" not in st.session_state:
        st.session_state["role"] = None

    st.title("Student Marks Chatbot")

    if st.session_state["role"] is None:
        st.subheader("Login")
        choice = st.radio("Select your role", ["Student", "Staff"], horizontal=True, key="login_role")

        if choice == "Student":
            st.text_input("Student ID / Roll No", key="login_student_id")
            st.text_input("Student password", type="password", key="login_student_pw")
        else:
            st.text_input("Staff ID / Username", key="login_staff_id")
            st.text_input("Staff password", type="password", key="login_staff_pw")

        if st.button("Continue"):
            if choice == "Staff":
                staff_id = st.session_state.get("login_staff_id", "").strip()
                staff_pw = st.session_state.get("login_staff_pw", "")
                if not staff_id or not staff_pw:
                    st.error("Enter staff ID and password.")
                elif STAFF_USERS.get(staff_id) != staff_pw:
                    st.error("Invalid staff ID or password.")
                else:
                    st.session_state["role"] = "Staff"
                    st.session_state["staff_id"] = staff_id
                    st.rerun()
            else:
                sid = st.session_state.get("login_student_id", "").strip()
                pw = st.session_state.get("login_student_pw", "")
                if not sid or not pw:
                    st.error("Enter student ID and password.")
                elif STUDENT_PASSWORDS.get(sid) != pw:
                    st.error("Invalid student ID or password.")
                else:
                    st.session_state["role"] = "Student"
                    st.session_state["student_id"] = sid
                    st.rerun()
        return

    # Logged in: show logout and respective GUI
    col1, col2 = st.columns([3, 1])
    with col1:
        role_label = st.session_state["role"]
        extra = ""
        if role_label == "Student":
            extra = f" (ID: {st.session_state.get('student_id', '')})"
        elif role_label == "Staff":
            extra = f" (ID: {st.session_state.get('staff_id', '')})"
        st.caption(f"Logged in as **{role_label}**{extra}")
    with col2:
        if st.button("Log out"):
            # Clear session so user returns to login screen
            st.session_state.clear()
            st.rerun()

    if st.session_state["role"] == "Staff":
        _show_staff_gui()
    else:
        _show_student_gui()


if __name__ == "__main__":
    main()


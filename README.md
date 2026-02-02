## Student Marks Chatbot (PDF Upload → Student Q&A)

This app lets **staff upload a PDF marksheet** (PDF-only), saves the marks into a local database, and lets **students ask in natural language** (example: "my mark in ds") to get a human-like reply.

### What you get
- **Staff tab**: upload marks PDF → parse → store in SQLite
- **Student tab**: enter Student ID + ask questions → answers from stored data

### PDF format requirement (important)
To reliably parse PDFs, the marks PDF must contain a clear table with columns like:

- `student_id` (or `roll_no`)
- `student_name` (optional)
- `subject` (or `course`)
- `mark` (or `marks`)

If your staff PDFs follow a different layout, we can adjust the parser to your exact template.

### Run locally

1) Create venv (optional)

```bash
python -m venv .venv
.\.venv\Scripts\activate
```

2) Install deps

```bash
pip install -r requirements.txt
```

3) Start the app

```bash
streamlit run app.py
```

### Demo questions
- "my mark in ds"
- "what is my mark in data structures"
- "show my marks"


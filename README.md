# BTVN #1 — Issue Triage mini-app

## Chạy

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
```

CLI:

```bash
python -m issue_triage.cli
python -m issue_triage.cli --issue "API login trả 503 cho toàn bộ user"
```

Streamlit:

```bash
streamlit run streamlit_app.py
```

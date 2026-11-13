# CivicOS

Explore NYC 311 requests in the Dashboard and Map Explorer. The included CSV contains the first 10,000 requests for October 2026, covering part of October 1.

Run these commands from the project root with your Python environment active:

```sh
python -m pip install -r requirements.txt
python app/db.py
python -m streamlit run app/streamlit_app.py
```

The second command builds the local SQLite sample at `data/processed/civicos.db`. Running it again skips request IDs already imported. The pages read this file. To use another database with the same schema, set `CIVICOS_DB_PATH` to its path before starting Streamlit.

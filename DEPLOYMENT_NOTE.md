# Hugging Face Space Deploy

This repository deploys the Pastel Streamlit dashboard through `app.py`, which
launches `app/dashboard_unified.py`.

The public Space should include:

- Streamlit app and source code
- derived feature CSVs
- derived metric CSVs
- non-executable model/dataset metadata JSON
- Thai-safe transcript QA, report, assistant, and fairness helpers

The public Space should exclude:

- raw CHAT transcripts beyond the project source dataset already tracked here
- uploaded/raw audio
- executable local secrets or access tokens

If `artifacts/screening_model.joblib` is absent, the Streamlit app falls back
to training the lightweight sklearn screening pipeline from
`data/combined_features.csv`.

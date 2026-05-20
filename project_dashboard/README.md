# Legacy Project Atlas + Model Trust Dashboard

This static dashboard is kept as a legacy local reference. The public project
now uses the Pastel Streamlit dashboard at `app/dashboard_unified.py` as the
single recommended surface for parent demo, clinician workflow, Model Trust,
and presentation.

## Coverage

- Overview metrics, realtime-style project signal, dataset mix, and dataset explorer
- Feature explorer and all 13 Streamlit feature definitions
- EDA scatter, distribution, correlation heatmap, and raw data preview
- Screening controls with uncertainty band, XAI contributions, severity scores, and parent concern checklist
- Model Trust dashboard: leaderboard, sensitivity/specificity/PPV/NPV, threshold playground, confusion matrix, calibration, Brier score, decision curve, uncertainty zone, subgroup robustness, leave-one-corpus-out, and model card
- Project Atlas: data inventory, corpus explorer, pipeline story, research evidence, glossary, safety/ethics, and presentation mode
- Audio-to-CHAT workflow with segment QA preview and generated CHAT example
- Model comparison, report figure tabs, progress deltas, trajectories, and first-vs-last table

## Run

From the project root:

```bash
python3 -m http.server 8080 --bind 127.0.0.1
```

Open:

```text
http://127.0.0.1:8080/project_dashboard/
```

The page references existing project figures from `reports/figures/`, so run
the server from the project root rather than inside this folder.

Refresh the trust metrics before presenting:

```bash
python src/classifier.py
```

That command regenerates `reports/metrics/*` trust CSVs and the model card in
`artifacts/model_card.json`.

## Deployment Status

Do not deploy this static dashboard as the public surface. Deploy the Pastel
Streamlit app through `app.py`, which launches `app/dashboard_unified.py`.

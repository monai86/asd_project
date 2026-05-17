# Deployment Guide

This project now has two public surfaces:

1. **Streamlit app** — Parent Public Demo + clinician/research workflow.
2. **Project Atlas static site** — presentation-ready data/model dashboard.

Pick the deployment target that matches the audience and constraints:

| Target | Cost | RAM | CPU/GPU | Upload size | Audio pipeline |
|--------|------|-----|---------|-------------|----------------|
| **Streamlit Community Cloud** | Free | 1 GB | CPU only | 200 MB | ⚠️ use `tiny`; audio may be slow |
| **Hugging Face Spaces (Streamlit)** | Free/paid | tier-based | CPU/GPU by tier | configurable | ✅ better for demo + model cache |
| **Netlify / Cloudflare Pages** | Free | static | none | n/a | ❌ Atlas only |
| **Self-host (Docker)** | Your infra | any | any | configurable | ✅ any |

---

## 1. Streamlit app: Streamlit Community Cloud

> Free hosting, automatic deploys from GitHub.  Recommended for the
> parent-facing demo when audio use is light.

### Steps

1. **Push to GitHub** (public or private repo).
2. Sign in at <https://share.streamlit.io> with your GitHub account.
3. Click **New app** → pick your repo → set:
   - **Branch:** `main`
   - **Main file path:** `app/dashboard.py`
   - **Python version:** `3.11`
4. Click **Deploy**.  First build takes several minutes (installing
   `torch`, `faster-whisper`, etc).

### Notes

- Streamlit Cloud reads `requirements.txt` automatically.
- The `[server]` section of `.streamlit/config.toml` is honoured.
- Upload limit on the free tier is effectively ~200 MB; the
  `maxUploadSize = 500` we set will be capped by the platform.
- The audio pipeline runs on CPU — use Whisper `tiny` for responsive UX.
- If the free tier runs out of memory while installing or loading audio
  dependencies, deploy the Streamlit app to Hugging Face Spaces or Docker.

---

## 2. Streamlit app: Hugging Face Spaces

Use this when you want a public URL for parents/advisors and a simpler
path to persistent model cache than Streamlit Cloud.

### Required files

- `app/dashboard.py`
- `requirements.txt`
- `packages.txt`
- `.streamlit/config.toml`
- `data/combined_features.csv`
- `data/longitudinal_features.csv`
- `reports/metrics/*.csv`
- `reports/figures/*.png`
- `artifacts/model_card.json`
- `artifacts/feature_schema.json`
- `artifacts/screening_model.joblib`

### Steps

1. Create a Hugging Face Space with **SDK = Streamlit**.
2. Push this repository to the Space remote.
3. Set the app file to `app/dashboard.py` if the Space asks for an entry
   point.
4. After the first build, open the Space and smoke-test:
   - Parent Public Demo loads
   - Screening page loads the model bundle
   - Audio page can run a short test with Whisper `tiny`

### Security

- Do not commit Hugging Face tokens into git remotes or files.
- If a token was ever embedded in a remote URL, rotate that token before
  pushing again.

---

## 3. Project Atlas static site: Netlify / Cloudflare Pages

The static Atlas should not publish raw `.cha` transcripts or the executable
`.joblib` model. Build the sanitized public bundle first:

```bash
bash scripts/build_public_atlas.sh
python3 -m http.server 8080 --bind 127.0.0.1 --directory dist/public_atlas
# open http://127.0.0.1:8080/
```

The build output is:

```text
dist/public_atlas/
```

It includes only:

- dashboard HTML/CSS/JS
- derived `combined_features.csv` and `longitudinal_features.csv`
- derived `reports/metrics/*.csv`
- generated `reports/figures/*.png`
- non-executable `artifacts/model_card.json`
- non-executable `artifacts/feature_schema.json`

### Netlify

This repository includes `netlify.toml`:

```toml
[build]
command = "bash scripts/build_public_atlas.sh"
publish = "dist/public_atlas"
```

Connect the GitHub repo to Netlify and deploy with the default config.

### Cloudflare Pages

Use:

```text
Build command: bash scripts/build_public_atlas.sh
Build output directory: dist/public_atlas
```

---

## 4. Self-host with Docker

```bash
# From project root
docker build -t asd-dashboard .
docker run -p 8501:8501 asd-dashboard
# Open http://localhost:8501
```

On Apple Silicon, build the same architecture you plan to deploy. For many
cloud hosts that means:

```bash
docker build --platform=linux/amd64 -t asd-dashboard .
```

The image includes PyTorch/audio dependencies, so the first build is large.
If you only need the presentation dashboard, deploy the static Atlas instead.

### With persistent audio / data mount
```bash
docker run -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/reports:/app/reports \
  asd-dashboard
```

### Production behind nginx
The container exposes `8501` and has a `HEALTHCHECK` on
`/_stcore/health`.  Put it behind nginx with TLS and forward to
`localhost:8501`.

---

## Environment variables

| Var | Purpose | Example |
|-----|---------|---------|
| `STREAMLIT_SERVER_PORT` | Override default port. | `8501` |
| `STREAMLIT_BROWSER_GATHER_USAGE_STATS` | Telemetry opt-out (already `false`). | `false` |

---

## Resource sizing

| Workload | Whisper model | Approx RAM | Approx time / 10 min audio |
|----------|--------------|-----------:|---------------------------:|
| Dashboard (typical) | `base`   | ~1.5 GB | 2-3 min on CPU |
| Higher accuracy     | `small`  | ~2.5 GB | 5-6 min on CPU |
| Research / evaluation | `medium` | ~5 GB | 15-20 min on CPU, 1-2 min on GPU |

---

## First-run model download

`faster-whisper` downloads the chosen model the first time it's used
(cached afterwards).  On a fresh container the first prediction will
take an additional ~30-120 seconds for the download.  The CI logs of Streamlit Cloud show this download.

---

## Troubleshooting

**“ffmpeg not found”**
→ Already installed in the `Dockerfile`.  On Streamlit Cloud, add a
`packages.txt` at the project root with a single line: `ffmpeg`.

**OOM during Whisper load**
→ Switch to the `tiny` or `base` model in the dashboard UI, or upgrade
the host RAM tier.

**pyannote diarization not working**
→ Set environment variable `HF_TOKEN` to your HuggingFace access token,
or leave `pyannote.audio` uninstalled; the pipeline automatically falls
back to the pitch heuristic.

**Docker healthcheck fails with curl missing**
→ The production Dockerfile installs `curl` because the healthcheck calls
`/_stcore/health`. Rebuild the image after pulling the latest Dockerfile.

**Static Atlas loads but charts are empty**
→ Rebuild with `bash scripts/build_public_atlas.sh` after rerunning
`python src/classifier.py`. Do not deploy `project_dashboard/` alone unless
the host also publishes the sibling `data/`, `reports/`, and `artifacts/`
folders.

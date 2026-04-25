# Deployment Guide

This project ships with three supported deployment targets.  Pick the
one that matches your constraints:

| Target | Cost | RAM | CPU/GPU | Upload size | Audio pipeline |
|--------|------|-----|---------|-------------|----------------|
| **Streamlit Community Cloud** | Free | 1 GB | CPU only | 200 MB | ✅ `tiny`/`base` Whisper |
| **Self-host (Docker)** | Your infra | any | any | configurable | ✅ any |

---

## 1. Streamlit Community Cloud (easiest)

> Free hosting, automatic deploys from GitHub.  Recommended for the
> advisor-facing demo.

### Steps

1. **Push to GitHub** (public or private repo).
2. Sign in at <https://share.streamlit.io> with your GitHub account.
3. Click **New app** → pick your repo → set:
   - **Branch:** `main`
   - **Main file path:** `app/dashboard.py`
   - **Python version:** `3.11`
4. Click **Deploy**.  First build takes ~5 minutes (installing
   `torch`, `faster-whisper`, etc).

### Notes

- Streamlit Cloud reads `requirements.txt` automatically.
- The `[server]` section of `.streamlit/config.toml` is honoured.
- Upload limit on the free tier is effectively ~200 MB; the
  `maxUploadSize = 500` we set will be capped by the platform.
- The audio pipeline runs on CPU — use Whisper `tiny` or `base` for
  responsive UX.

---

## 2. Self-host with Docker

```bash
# From project root
docker build -t asd-dashboard .
docker run -p 8501:8501 asd-dashboard
# Open http://localhost:8501
```

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

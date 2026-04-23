# Deployment Guide

This project ships with three supported deployment targets.  Pick the
one that matches your constraints:

| Target | Cost | RAM | CPU/GPU | Upload size | Audio pipeline |
|--------|------|-----|---------|-------------|----------------|
| **Streamlit Community Cloud** | Free | 1 GB | CPU only | 200 MB | ✅ `tiny`/`base` Whisper |
| **HuggingFace Spaces** (Docker) | Free | 16 GB | CPU / optional GPU | 500 MB+ | ✅ up to `medium` |
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

## 2. HuggingFace Spaces (more RAM, optional GPU)

> Also free, more generous RAM limits (16 GB on CPU tier), and you can
> bump to a paid GPU tier if you want to run Whisper `medium` / `large`.

### Steps

1. Create a new Space at <https://huggingface.co/new-space>:
   - **SDK:** `Docker`
   - **Hardware:** `CPU basic` (free) or `CPU upgrade` / `T4 small`.
2. Clone the Space locally:
   ```bash
   git clone https://huggingface.co/spaces/<your-username>/asd-dashboard
   ```
3. Copy your project files into the Space repo (the `Dockerfile`
   and `.dockerignore` we shipped are already HF-compatible).
4. Create a `README.md` at the Space root with the HF front-matter:
   ```yaml
   ---
   title: ASD Assessment Dashboard
   emoji: 🧩
   colorFrom: indigo
   colorTo: purple
   sdk: docker
   app_port: 8501
   pinned: true
   ---
   ```
5. `git add -A && git commit -m "Initial deploy" && git push`.

### Optional: pyannote diarization on HF

If you want the higher-quality pyannote diarizer instead of the pitch
heuristic:

1. Accept the gated model terms at
   <https://huggingface.co/pyannote/speaker-diarization-3.1>.
2. In your Space → **Settings** → **Variables and secrets**, add a new
   secret `HF_TOKEN` with your HuggingFace access token.
3. Uncomment `pyannote.audio` in `requirements.txt`.
4. Redeploy.

---

## 3. Self-host with Docker

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
| `HF_TOKEN` | HuggingFace access token — enables pyannote diarization. | `hf_xxx...` |
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
take an additional ~30-120 seconds for the download.  The CI logs of
both Streamlit Cloud and HuggingFace Spaces show this download.

---

## Troubleshooting

**“ffmpeg not found”**
→ Already installed in the `Dockerfile`.  On Streamlit Cloud, add a
`packages.txt` at the project root with a single line: `ffmpeg`.

**OOM during Whisper load**
→ Switch to the `tiny` or `base` model in the dashboard UI, or upgrade
the host RAM tier.

**“HF_TOKEN is not set” when using pyannote**
→ Either set the token (see section 2) or leave pyannote uninstalled;
the pipeline automatically falls back to the pitch heuristic.

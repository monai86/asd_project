# Production Deployment & CI/CD Setup Guide (คู่มือการติดตั้งระบบออนไลน์และการบิลด์อัตโนมัติ)

This guide explains how to host the Speech Assessment application online so therapists and clinicians can access it through their web browsers, and how to set up GitHub CI/CD so that updating the code automatically updates the live website and backend.

---

## 🏗️ 1. Backend API Hosting (การติดตั้งระบบหลังบ้านบน Render หรือ Railway)

Since the backend is written in Python (using Whisper, PyThaiNLP, and PyTorch), it is packaged inside a [Dockerfile](file:///../Dockerfile). You can deploy it to platforms that support Docker, such as **Render** (recommended for ease of use) or **Railway**.

### Render Setup Steps (ขั้นตอนการตั้งค่าบน Render):
1. Sign up/Log in to [Render](https://render.com).
2. Click **New +** and select **Web Service**.
3. Connect your **GitHub Repository** containing this project.
4. Configure the Web Service settings:
   - **Name:** `asd-speech-backend` (or your preferred name)
   - **Environment:** `Docker` (Render will automatically detect the `Dockerfile` at the root)
   - **Region:** Select the closest region to your users (e.g., Singapore)
   - **Branch:** `main`
5. Add the following **Environment Variables** in the Render Dashboard (variables are kept secure and are not public):
   - `OPENAI_API_KEY`: Your OpenAI API key (for the Whisper API strategy).
   - `HF_TOKEN`: (Optional) Hugging Face token if using the pyannote speaker diarization backend.
   - `PORT`: `8000` (Render binds to the port specified in environment variables).
6. Click **Create Web Service**. Render will compile the Docker container and deploy it to a public URL (e.g., `https://asd-speech-backend.onrender.com`).
7. Copy your deployed Backend URL for use in the frontend configuration.

---

## 🏠 2. Frontend Applications Deployment (การติดตั้งหน้าเว็บระบบบน Cloudflare Pages)

The public screening and presentation apps are static Cloudflare Pages sites.
The Therapist App is Next.js and requires Vercel or another supported Node runtime.

### Cloudflare Pages Setup Steps (ขั้นตอนการตั้งค่าบน Cloudflare):
1. Sign up/Log in to [Cloudflare Dashboard](https://dash.cloudflare.com) and go to **Workers & Pages**.
2. Click **Create Application** -> **Pages** -> **Connect to Git**.
3. Select your GitHub repository.
4. Configure the settings for each app you want to build:

#### A. Therapist App (`apps/therapist-app-v2`):
- **Project Name:** `asd-therapist-app-v2`
- **Framework Preset:** `Next.js`
- **Build Command:** `npm run build`
- **Root Directory:** `apps/therapist-app-v2`
- **Environment Variables (Variables ในการติดตั้ง):**
  - `NEXT_PUBLIC_API_BASE_URL`: deployed `apps/api` base URL

#### B. Public Screening App (`public-screening`):
- **Project Name:** `asd-public-screening`
- **Build Command:** `npm run build`
- **Build Output Directory:** `dist`
- **Root Directory:** `public-screening`

---

## ⚡ 3. Setting Up GitHub Actions CI/CD (การเชื่อมต่อบิลด์อัตโนมัติเมื่อกด Push โค้ด)

We have configured a GitHub Actions pipeline in [.github/workflows/deploy.yml](file:///../.github/workflows/deploy.yml). Every time you push code updates to the `main` branch on GitHub:
1. GitHub will run your Python unit tests to make sure there are no regressions.
2. It will build and upload the updated React apps to Cloudflare Pages.
3. It will ping Render/Railway to trigger an automatic rebuild and redeployment of the backend.

### Required GitHub Secrets (การตั้งค่าความลับบน GitHub):
Go to your GitHub Repository -> **Settings** -> **Secrets and variables** -> **Actions** -> **New repository secret** and add:

| Secret Name | Value Description |
|-------------|-------------------|
| `CLOUDFLARE_API_TOKEN` | Cloudflare API Token (with Pages Edit permissions). |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Account ID. |
| `VITE_PROCESSING_API_BASE_URL` | Your deployed Render backend URL. |
| `VITE_SUPABASE_URL` | Your Supabase project URL. |
| `VITE_SUPABASE_ANON_KEY` | Your Supabase public anon key. |
| `RENDER_DEPLOY_HOOK_URL` | Render Deploy Webhook URL (Found in Render Dashboard under Deploy Hook). |

Now, whenever you push an update to GitHub, the entire system will be tested, compiled, and deployed automatically!
ข้อมูลความคืบหน้าและการตั้งค่าหลังบ้านจะอัปเดตออนไลน์โดยอัตโนมัติเมื่อมีการเปลี่ยนแปลงโค้ดใน GitHub ครับ

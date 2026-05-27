# ASD Public Screening Support Web App

This is a bilingual (Thai/English) public-facing screening support web application built with **Vite** and **Vanilla HTML/CSS/JS**. It serves as an educational and supportive tool for parents, caregivers, students, or anyone interested in child developmental speech-language concern indicators.

## ⚠️ Important Safety Boundary (Non-Diagnostic)
This app **does NOT diagnose ASD**. It is strictly for screening support and educational guidance. It clearly communicates to users that only qualified professionals (such as developmental pediatricians, speech-language therapists, or child psychologists) can perform clinical diagnostic assessments.
- Wording used: *"screening support"*, *"developmental concern level"*, *"risk indicators"*, and *"recommend consulting a qualified professional"*.
- Data Privacy: **Zero data retention**. All data resides entirely in the user's browser session (using `sessionStorage`) and is cleared when clicking "Start Over" or closing the tab.

---

## Page Structure

1. **Landing Page (`index.html`)**:
   - Introduces the screening support tool.
   - Explicit disclaimers highlighting what the tool does and does not do.
   - Call to action: "Start Screening Support".

2. **Screening Questionnaire (`screening.html`)**:
   - Age range selection (under 12 months to 60+ months).
   - 14 Likert scale (1-5) questions covering:
     - Speech & Language Concerns (5 questions)
     - Social Communication Concerns (5 questions)
     - Repetitive Behaviors (4 questions)
   - Optional free-text observation/transcript notes box.
   - Input validation (highlights blank fields with red outlines).

3. **Results Page (`results.html`)**:
   - Dynamic concern level display (Low / Moderate / High) with supporting explanations.
   - Interactive SVG concern gauge with an animated needle pointing to the final normalized score (0–100).
   - Card breakdown of scores across the three concern categories.
   - Expandable accordion for item-by-item response details.
   - Action buttons: "Download Summary" (initiates print-optimized report layout) and "Start Over" (wipes data and restarts).

4. **Educational FAQs (`education.html`)**:
   - Interactive accordion list covering general FAQs, indicators, and details about the screening tool.

---

## Local Development & Setup

### Prerequisites
- Node.js (version 18 or higher recommended)
- npm (Node Package Manager)

### Commands
From the `public-screening` directory:

1. **Install Dependencies**:
   ```bash
   npm install
   ```

2. **Start Dev Server**:
   ```bash
   npm run dev
   ```
   *Typically hosts locally at `http://localhost:3000` or the next available port.*

3. **Compile / Build for Production**:
   ```bash
   npm run build
   ```
   *Compiles all assets and HTML outputs into the `dist/` directory in under a second.*

4. **Preview Production Build Locally**:
   ```bash
   npm run preview
   ```

---

## Cloudflare Pages Deployment Configuration

To deploy this sub-app on Cloudflare Pages:

1. Log in to the **Cloudflare Dashboard** and navigate to **Workers & Pages**.
2. Click **Create Application** → **Pages** → **Connect to Git**.
3. Choose the repository and set the following build settings:
   - **Framework preset**: `Vite` (or None)
   - **Build command**: `npm run build`
   - **Build output directory**: `dist`
   - **Root directory**: `public-screening`
4. Click **Save and Deploy**. Cloudflare Pages will automatically compile and host the app, updating whenever changes are pushed to your main branch.

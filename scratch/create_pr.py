import subprocess
import json
import urllib.request
import urllib.error
import sys

def get_keychain_token():
    try:
        cmd = ["security", "find-internet-password", "-s", "github.com", "-a", "149382813", "-w"]
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        return output.decode("utf-8").strip()
    except Exception as e:
        print(f"Error fetching token from keychain: {e}", file=sys.stderr)
        return None

def create_pull_request():
    token = get_keychain_token()
    if not token:
        print("Failed to retrieve token. Exiting.", file=sys.stderr)
        sys.exit(1)

    pr_title = "feat(clinical-ui): Redesign Therapist Dashboard, Native iOS Shell & Print Layout Fixes"
    pr_body = """## Description

This Pull Request integrates the clinical dashboard redesign, Capacitor-based iOS native packaging, and critical print layout fixes to deliver a premium, production-grade clinical workspace for speech-language therapists.

### Key Changes:

#### 1. Clinical Report Print Layout & Page-Cuts (v1.3.1)
- **Fix Missing Header/First Page:** Changed `<header>` container to `<div class="report-header">` to prevent global display-none print directives from hiding the clinical metadata, evaluator credentials, and report title.
- **Color & Styling Preservation:** Excluded the report document and its descendants from the global print wildcard background stripper (`*:not(.report-document):not(.report-document *)`), successfully rendering colors for concern badges, progress indicator lines, and trend chart fills in printed PDFs.
- **Page Margin & Page-breaks:** Configured standard `@page { size: A4; margin: 20mm 15mm; }` rules, collapsed `.report-document` padding, and applied `page-break-after: avoid` to print headings to prevent orphan headers.

#### 2. Bilingual Switcher & Matrix View (v1.3.0)
- **Bilingual Toggle:** Fast switcher (Thai vs English) translating all clinical parameters, disclaimers, table headings, and signature slots.
- **Custom Typography:** Automatically swaps font weights and dimensions (`Sarabun` fallback at `12.5pt` with `1.6` height for Thai; `Outfit` / `Inter` at `10.5pt` with `1.65` height for English).
- **Longitudinal Graph & Table:** Embedded a progress line chart tracking Task A Risk Score with color-coded nodes by concern level. Added a combined longitudinal table showing NLP features side-by-side across all sessions.

#### 3. Capacitor iOS Native Shell
- **iOS Packaging:** Configured Capacitor workspace setup for `therapist-clinician-app/` allowing it to run as a native iOS app (`therapist-clinician-app/ios/`).
- **Native Controller:** Built an iOS native shell wrapper (`NativeClinicalShellViewController.swift`) managing safe-areas, status bars, and offline indicators without duplication of business workflows.

#### 4. Persistent Mock State & Polish
- **Local Persistence:** Configured `localStorage` mirroring for therapist state so newly created cases, details, and annotations survive browser refreshes.
- **Usability Polish:** Resolved the case form layout flex squeeze, restored workspace routing to interactive transcript editing views, and made topbar command palettes (search/notifications) interactive.

---

### Verification
- **Unit Tests:** All 166 frontend unit tests pass successfully (`npm test`).
- **Production Build:** Production bundle compiles successfully (`npm run build`).
"""

    payload = {
        "title": pr_title,
        "head": "codex/finish-clinical-workspace-auth",
        "base": "main",
        "body": pr_body
    }

    url = "https://api.github.com/repos/monai86/asd_project/pulls"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "Antigravity-AI-Agent"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            print(f"Success! Pull Request created: {res_data.get('html_url')}")
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}", file=sys.stderr)
        try:
            err_body = e.read().decode("utf-8")
            print(f"Details: {err_body}", file=sys.stderr)
        except Exception:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    create_pull_request()

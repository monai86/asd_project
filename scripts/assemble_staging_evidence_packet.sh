#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/docs/release_artifacts/staging_packet}"
DATE_STAMP="$(date +%Y-%m-%d)"
TIME_STAMP="$(date +%H%M%S)"
SLUG="${1:-staging-evidence-packet-assembled}"
OUTPUT_PATH="$OUTPUT_DIR/${DATE_STAMP}_${TIME_STAMP}_${SLUG}.md"

PROJECT_SETUP_EVIDENCE="${PROJECT_SETUP_EVIDENCE:-$ROOT_DIR/docs/release_artifacts/project_setup/2026-06-28_140742_lingualens-org-created.md}"
AUTH_VERIFIER_EVIDENCE="${AUTH_VERIFIER_EVIDENCE:-$ROOT_DIR/docs/release_artifacts/auth_verifier/2026-06-28_141705_cbhwxklvcpgizeqriqxi-jwks-url.md}"
AUTH_VERIFIER_SUMMARY="${AUTH_VERIFIER_SUMMARY:-$ROOT_DIR/docs/release_artifacts/auth_verifier/verifier-run-summary.md}"
TENANT_SAFETY_EVIDENCE="${TENANT_SAFETY_EVIDENCE:-}"
TENANT_SAFETY_SUMMARY="${TENANT_SAFETY_SUMMARY:-$ROOT_DIR/docs/release_artifacts/tenant_safety/tenant-safety-run-summary.md}"
STAGING_API_URL="${STAGING_API_URL:-${STAGING_API_BASE_URL:-}}"
STAGING_APP_URL="${STAGING_APP_URL:-${STAGING_APP_BASE_URL:-}}"
OPERATOR_NAME="${OPERATOR_NAME:-}"
REVIEWER_NAME="${REVIEWER_NAME:-}"
PACKET_RESULT="${PACKET_RESULT:-in_progress}"
SUPABASE_PROJECT_REF="${SUPABASE_PROJECT_REF:-cbhwxklvcpgizeqriqxi}"

mkdir -p "$OUTPUT_DIR"

if [[ -e "$OUTPUT_PATH" ]]; then
  echo "Refusing to overwrite existing file: $OUTPUT_PATH" >&2
  exit 1
fi

COMMIT_SHA=""
if git -C "$ROOT_DIR" rev-parse --short HEAD >/dev/null 2>&1; then
  COMMIT_SHA="$(git -C "$ROOT_DIR" rev-parse --short HEAD)"
fi

artifact_status() {
  local path="$1"
  if [[ -n "$path" && -f "$path" ]]; then
    printf 'present'
  elif [[ -n "$path" ]]; then
    printf 'missing'
  else
    printf 'pending'
  fi
}

AUTH_SUMMARY_STATUS="$(artifact_status "$AUTH_VERIFIER_SUMMARY")"
TENANT_SUMMARY_STATUS="$(artifact_status "$TENANT_SAFETY_SUMMARY")"
TENANT_EVIDENCE_STATUS="$(artifact_status "$TENANT_SAFETY_EVIDENCE")"

cat >"$OUTPUT_PATH" <<EOF
# Staging Evidence Packet

- Date: ${DATE_STAMP}
- Commit: ${COMMIT_SHA}
- Operator: ${OPERATOR_NAME}
- Reviewer: ${REVIEWER_NAME}
- Staging API URL: ${STAGING_API_URL}
- Staging therapist app URL: ${STAGING_APP_URL}
- Supabase project ref: ${SUPABASE_PROJECT_REF}
- Result: ${PACKET_RESULT}

## Included Artifacts

| Artifact | Path | Status | Notes |
|---|---|---|---|
| Project setup evidence | ${PROJECT_SETUP_EVIDENCE} | $(artifact_status "$PROJECT_SETUP_EVIDENCE") | Confirmed org/project creation and runtime inputs. |
| Auth verifier evidence | ${AUTH_VERIFIER_EVIDENCE} | $(artifact_status "$AUTH_VERIFIER_EVIDENCE") | Staging verifier evidence file. |
| Auth verifier run summary | ${AUTH_VERIFIER_SUMMARY} | ${AUTH_SUMMARY_STATUS} | Bundle output after preflight and core/lifecycle probes. |
| Tenant-safety evidence | ${TENANT_SAFETY_EVIDENCE} | ${TENANT_EVIDENCE_STATUS} | Generated tenant-safety evidence file. |
| Tenant-safety run summary | ${TENANT_SAFETY_SUMMARY} | ${TENANT_SUMMARY_STATUS} | Bundle output after tenant-safety matrix. |

## Preconditions

- [ ] Staging runtime is non-mock.
- [ ] Auth mode is \`supabase\`.
- [ ] Verifier mode is \`jwks_url\`.
- [ ] Public signup is off.
- [ ] MFA requires \`aal2\` before app access.

## Gate Results

| Gate | Result | Evidence reference | Reviewer notes |
|---|---|---|---|
| Auth verifier | ${AUTH_SUMMARY_STATUS} | ${AUTH_VERIFIER_SUMMARY} |  |
| Tenant-safety matrix | ${TENANT_SUMMARY_STATUS} | ${TENANT_SAFETY_SUMMARY} |  |
| JWKS operational checks | pending | ${AUTH_VERIFIER_EVIDENCE} |  |
| Revocation or fail-closed checks | pending | ${AUTH_VERIFIER_SUMMARY} / ${TENANT_SAFETY_SUMMARY} |  |

## Remaining Risks

- None / describe:

## Go / No-Go Recommendation

- Recommendation:
- Conditions before production promotion:
- Sign-off:
EOF

printf '%s\n' "$OUTPUT_PATH"

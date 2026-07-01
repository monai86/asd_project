#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/create_supabase_runtime_env_snippets.sh

Optional environment:
  OUTPUT_DIR                     Defaults to docs/release_artifacts/runtime_env
  STAGING_API_BASE_URL           Optional placeholder override
  STAGING_APP_BASE_URL           Optional placeholder override
  PRODUCTION_API_BASE_URL        Optional placeholder override
  PRODUCTION_APP_BASE_URL        Optional placeholder override
  STAGING_JOB_QUEUE_MODE         Optional placeholder override
  PRODUCTION_JOB_QUEUE_MODE      Optional placeholder override
  STAGING_SECRET_STORE_PROVIDER  Optional placeholder override
  PRODUCTION_SECRET_STORE_PROVIDER Optional placeholder override
  STAGING_OBSERVABILITY_PROVIDER Optional placeholder override
  PRODUCTION_OBSERVABILITY_PROVIDER Optional placeholder override
  STAGING_CRITICAL_ALERT_ROUTE   Optional placeholder override
  PRODUCTION_CRITICAL_ALERT_ROUTE Optional placeholder override
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$ROOT_DIR/docs/release_artifacts/runtime_env}"
DATE_STAMP="$(date +%Y-%m-%d)"
TIME_STAMP="$(date +%H%M%S)"

mkdir -p "$OUTPUT_DIR"

STAGING_FILE="$OUTPUT_DIR/${DATE_STAMP}_${TIME_STAMP}_staging_supabase.env"
PRODUCTION_FILE="$OUTPUT_DIR/${DATE_STAMP}_${TIME_STAMP}_production_supabase.env"

cat >"$STAGING_FILE" <<EOF
# Staging frontend
NEXT_PUBLIC_API_BASE_URL=${STAGING_API_BASE_URL:-<staging-api-base-url>/api/v1}
NEXT_PUBLIC_SUPABASE_URL=https://cbhwxklvcpgizeqriqxi.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_zC7wscUPHNtoqQb4amCEEQ_K2dCC5si

# Staging API
LINGUALENS_MOCK_MODE=false
LINGUALENS_AUTH_MODE=supabase
LINGUALENS_SUPABASE_JWT_VERIFICATION_MODE=jwks_url
LINGUALENS_SUPABASE_JWT_JWKS_URL=https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1/.well-known/jwks.json
LINGUALENS_SUPABASE_JWT_JWKS_CACHE_TTL_SECONDS=300
LINGUALENS_SUPABASE_JWT_ISSUER=https://cbhwxklvcpgizeqriqxi.supabase.co/auth/v1
LINGUALENS_SUPABASE_JWT_AUDIENCE=authenticated
LINGUALENS_SUPABASE_REQUIRE_MFA=true
LINGUALENS_SUPABASE_REQUIRE_INVITATION=true

# Production-like runtime requirements
LINGUALENS_REPOSITORY_MODE=sql
LINGUALENS_STORAGE_MODE=supabase_private
LINGUALENS_JOB_QUEUE_MODE=${STAGING_JOB_QUEUE_MODE:-<durable-managed-mode>}
LINGUALENS_SECRET_STORE_PROVIDER=${STAGING_SECRET_STORE_PROVIDER:-<managed-secret-store-provider>}
LINGUALENS_OBSERVABILITY_ENABLED=true
LINGUALENS_OBSERVABILITY_PROVIDER=${STAGING_OBSERVABILITY_PROVIDER:-<approved-observability-provider>}
LINGUALENS_CRITICAL_ALERT_ROUTE=${STAGING_CRITICAL_ALERT_ROUTE:-<critical-alert-route>}

# Optional operator notes
STAGING_APP_BASE_URL=${STAGING_APP_BASE_URL:-<staging-app-base-url>}
EOF

cat >"$PRODUCTION_FILE" <<EOF
# Production frontend
NEXT_PUBLIC_API_BASE_URL=${PRODUCTION_API_BASE_URL:-<production-api-base-url>/api/v1}
NEXT_PUBLIC_SUPABASE_URL=https://rftslmbgbudqsypknzss.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_publishable_Yrk22_dt_oSdAa0ov-FGCA_-ZBylare

# Production API
LINGUALENS_MOCK_MODE=false
LINGUALENS_AUTH_MODE=supabase
LINGUALENS_SUPABASE_JWT_VERIFICATION_MODE=jwks_url
LINGUALENS_SUPABASE_JWT_JWKS_URL=https://rftslmbgbudqsypknzss.supabase.co/auth/v1/.well-known/jwks.json
LINGUALENS_SUPABASE_JWT_JWKS_CACHE_TTL_SECONDS=300
LINGUALENS_SUPABASE_JWT_ISSUER=https://rftslmbgbudqsypknzss.supabase.co/auth/v1
LINGUALENS_SUPABASE_JWT_AUDIENCE=authenticated
LINGUALENS_SUPABASE_REQUIRE_MFA=true
LINGUALENS_SUPABASE_REQUIRE_INVITATION=true

# Production runtime requirements
LINGUALENS_REPOSITORY_MODE=sql
LINGUALENS_STORAGE_MODE=supabase_private
LINGUALENS_JOB_QUEUE_MODE=${PRODUCTION_JOB_QUEUE_MODE:-<durable-managed-mode>}
LINGUALENS_SECRET_STORE_PROVIDER=${PRODUCTION_SECRET_STORE_PROVIDER:-<managed-secret-store-provider>}
LINGUALENS_OBSERVABILITY_ENABLED=true
LINGUALENS_OBSERVABILITY_PROVIDER=${PRODUCTION_OBSERVABILITY_PROVIDER:-<approved-observability-provider>}
LINGUALENS_CRITICAL_ALERT_ROUTE=${PRODUCTION_CRITICAL_ALERT_ROUTE:-<critical-alert-route>}

# Optional operator notes
PRODUCTION_APP_BASE_URL=${PRODUCTION_APP_BASE_URL:-<production-app-base-url>}
EOF

printf '%s\n%s\n' "$STAGING_FILE" "$PRODUCTION_FILE"

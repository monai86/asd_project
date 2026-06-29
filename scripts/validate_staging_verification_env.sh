#!/usr/bin/env bash

set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  bash scripts/validate_staging_verification_env.sh [env-file]

When an env file is provided, the script sources it and validates the staged
verification variables. Without a file argument, the current shell environment
is validated.
EOF
}

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ $# -gt 1 ]]; then
  usage >&2
  exit 1
fi

if [[ $# -eq 1 ]]; then
  ENV_FILE="$1"
  if [[ ! -f "$ENV_FILE" ]]; then
    echo "Env file not found: $ENV_FILE" >&2
    exit 1
  fi
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: $name" >&2
    exit 1
  fi
}

reject_placeholder() {
  local name="$1"
  local value="${!name:-}"

  if [[ -z "$value" ]]; then
    echo "Missing required environment variable: $name" >&2
    exit 1
  fi

  if [[ "$value" == *"<"* || "$value" == *">"* ]]; then
    echo "Placeholder value not replaced for $name: $value" >&2
    exit 1
  fi

  case "$value" in
    org_a|org_b|"<jwt>"|"<membership_id>"|"<case_a_1>"|"<case_b_1>"|\
    https://\<staging-api-host\>/api/v1|https://\<staging-therapist-app-host\>)
      echo "Placeholder value not replaced for $name: $value" >&2
      exit 1
      ;;
  esac
}

require_prefix() {
  local name="$1"
  local prefix="$2"
  local value="${!name:-}"
  if [[ "$value" != "$prefix"* ]]; then
    echo "Unexpected value for $name: expected prefix $prefix, got $value" >&2
    exit 1
  fi
}

require_exact_suffix() {
  local name="$1"
  local suffix="$2"
  local value="${!name:-}"
  if [[ "$value" != *"$suffix" ]]; then
    echo "Unexpected value for $name: expected suffix $suffix, got $value" >&2
    exit 1
  fi
}

reject_substring() {
  local name="$1"
  local fragment="$2"
  local value="${!name:-}"
  if [[ "$value" == *"$fragment"* ]]; then
    echo "Unexpected value for $name: must not contain $fragment, got $value" >&2
    exit 1
  fi
}

require_jwt_like() {
  local name="$1"
  local value="${!name:-}"
  if [[ ! "$value" =~ ^[^.]+\.[^.]+\.[^.]+$ ]]; then
    echo "Unexpected value for $name: expected JWT-like token shape, got $value" >&2
    exit 1
  fi
}

require_env STAGING_API_BASE_URL
require_env STAGING_APP_BASE_URL
require_env STAGING_SUPABASE_PROJECT_REF
require_env ORG_A_ID
require_env ORG_B_ID
require_env ORG_A_CASE_ID
require_env ORG_B_CASE_ID
require_env TOKEN_THERAPIST_A_ASSIGNED
require_env TOKEN_THERAPIST_A_UNASSIGNED
require_env TOKEN_SUPERVISOR_A
require_env TOKEN_ORG_ADMIN_A
require_env TOKEN_PLATFORM_OPERATOR_A
require_env TOKEN_THERAPIST_B_ASSIGNED

reject_placeholder STAGING_API_BASE_URL
reject_placeholder STAGING_APP_BASE_URL
reject_placeholder STAGING_SUPABASE_PROJECT_REF
reject_placeholder ORG_A_ID
reject_placeholder ORG_B_ID
reject_placeholder ORG_A_CASE_ID
reject_placeholder ORG_B_CASE_ID
reject_placeholder TOKEN_THERAPIST_A_ASSIGNED
reject_placeholder TOKEN_THERAPIST_A_UNASSIGNED
reject_placeholder TOKEN_SUPERVISOR_A
reject_placeholder TOKEN_ORG_ADMIN_A
reject_placeholder TOKEN_PLATFORM_OPERATOR_A
reject_placeholder TOKEN_THERAPIST_B_ASSIGNED

require_prefix STAGING_API_BASE_URL "https://"
require_prefix STAGING_APP_BASE_URL "https://"
require_exact_suffix STAGING_API_BASE_URL "/api/v1"
reject_substring STAGING_APP_BASE_URL "/api/v1"

if [[ "$STAGING_SUPABASE_PROJECT_REF" != "cbhwxklvcpgizeqriqxi" ]]; then
  echo "Unexpected staging project ref: $STAGING_SUPABASE_PROJECT_REF" >&2
  exit 1
fi

if [[ "$STAGING_API_BASE_URL" == "$STAGING_APP_BASE_URL" ]]; then
  echo "STAGING_API_BASE_URL and STAGING_APP_BASE_URL must not be identical." >&2
  exit 1
fi

require_jwt_like TOKEN_THERAPIST_A_ASSIGNED
require_jwt_like TOKEN_THERAPIST_A_UNASSIGNED
require_jwt_like TOKEN_SUPERVISOR_A
require_jwt_like TOKEN_ORG_ADMIN_A
require_jwt_like TOKEN_PLATFORM_OPERATOR_A
require_jwt_like TOKEN_THERAPIST_B_ASSIGNED

if [[ -n "${TOKEN_THERAPIST_INVITATION_PENDING:-}" ]]; then
  reject_placeholder TOKEN_THERAPIST_INVITATION_PENDING
  require_jwt_like TOKEN_THERAPIST_INVITATION_PENDING
fi

if [[ -n "${TOKEN_THERAPIST_AAL1:-}" ]]; then
  reject_placeholder TOKEN_THERAPIST_AAL1
  require_jwt_like TOKEN_THERAPIST_AAL1
fi

if [[ -n "${TOKEN_THERAPIST_INACTIVE_MEMBERSHIP:-}" ]]; then
  reject_placeholder TOKEN_THERAPIST_INACTIVE_MEMBERSHIP
  require_jwt_like TOKEN_THERAPIST_INACTIVE_MEMBERSHIP
fi

if [[ -n "${REVOCATION_MEMBERSHIP_ID:-}" ]]; then
  reject_placeholder REVOCATION_MEMBERSHIP_ID
fi

echo "Staging verification environment is ready."

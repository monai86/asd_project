#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

VENV_PYTHON="${ROOT_DIR}/.venv312/bin/python"
if [ ! -f "${VENV_PYTHON}" ]; then
  VENV_PYTHON="/Users/porschecaa/lingualens/.venv312/bin/python"
fi
if [ ! -f "${VENV_PYTHON}" ]; then
  VENV_PYTHON="${ROOT_DIR}/.venv/bin/python"
fi
if [ ! -f "${VENV_PYTHON}" ]; then
  VENV_PYTHON="python3"
fi

echo "==> Running v1.7.0 API Unit Test Gate..."
cd "${ROOT_DIR}/apps/api"
rtk env PYTHONPATH=. "${VENV_PYTHON}" -m pytest \
  tests/test_v170_config.py \
  tests/test_speech_pipeline_persistence.py \
  tests/test_audio_media_service.py \
  tests/test_audio_intake_limits.py \
  tests/test_local_faster_whisper_provider.py \
  tests/test_transcription_job_lifecycle.py \
  tests/test_asr_completeness_service.py \
  tests/test_speaker_mapping.py \
  tests/test_v170_qa_policy.py \
  tests/test_chat_subset_v170.py \
  tests/test_chat_roundtrip_v170.py \
  tests/test_v170_tokenizer.py \
  tests/test_v170_descriptive_features.py \
  tests/test_v170_findings.py -q

echo "==> Running v1.7.0 Vertical Slice Audio Gate..."
rtk env PYTHONPATH=. "${VENV_PYTHON}" -m pytest tests/test_v170_vertical_slice.py -q -m audio

echo "==> Running v1.7.0 Frontend Unit Test Gate..."
cd "${ROOT_DIR}/apps/lingualens-app"
npm test -- \
  src/__tests__/audio-file-upload-panel.test.tsx \
  src/__tests__/speaker-mapping-panel.test.tsx \
  src/__tests__/qa-limitations-panel.test.tsx \
  src/__tests__/session-findings-v170.test.tsx \
  src/__tests__/browser-audio-recorder.test.tsx \
  src/__tests__/experimental-transcription-service.test.ts

echo "==> All v1.7.0 speech pipeline checks passed successfully!"

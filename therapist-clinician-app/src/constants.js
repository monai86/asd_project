export const RUNTIME_MODES = {
  MOCK: "mock",
  LOCAL_DEV: "local_dev",
  PILOT_BACKEND: "pilot_backend"
};

function readActiveRuntimeMode() {
  const viteMode = typeof import.meta !== "undefined" ? import.meta.env?.VITE_RUNTIME_MODE : null;
  const windowMode = typeof window !== "undefined" ? window.__ASD_RUNTIME_MODE__ : null;
  return windowMode || viteMode || RUNTIME_MODES.MOCK;
}

export const ACTIVE_RUNTIME_MODE = readActiveRuntimeMode();
export const MOCK_MODE = ACTIVE_RUNTIME_MODE === RUNTIME_MODES.MOCK;

export const DATA_MODES = ["mock", "localStorage", "database_placeholder", "api", "supabase"];
export const FILE_STORAGE_MODES = [
  "metadata_only",
  "browser_preview",
  "backend_placeholder",
  "secure_backend",
  "supabase_storage"
];
export const PROCESSING_MODES = ["mock", "api_placeholder", "backend"];
export const AUTH_MODES = ["mock", "provider_placeholder", "local_dev", "supabase", "enterprise_oidc_placeholder"];

function getDefaultDataMode() {
  if (ACTIVE_RUNTIME_MODE === RUNTIME_MODES.MOCK) return "mock";
  if (ACTIVE_RUNTIME_MODE === RUNTIME_MODES.PILOT_BACKEND) return "supabase";
  return "api";
}

function getDefaultFileStorageMode() {
  if (ACTIVE_RUNTIME_MODE === RUNTIME_MODES.MOCK) return "metadata_only";
  if (ACTIVE_RUNTIME_MODE === RUNTIME_MODES.LOCAL_DEV) return "metadata_only";
  return "supabase_storage";
}

function getDefaultProcessingMode() {
  if (ACTIVE_RUNTIME_MODE === RUNTIME_MODES.MOCK) return "mock";
  if (ACTIVE_RUNTIME_MODE === RUNTIME_MODES.LOCAL_DEV) return "mock";
  return "backend";
}

function getDefaultAuthMode() {
  if (ACTIVE_RUNTIME_MODE === RUNTIME_MODES.MOCK) return "mock";
  if (ACTIVE_RUNTIME_MODE === RUNTIME_MODES.LOCAL_DEV) return "local_dev";
  return "supabase";
}

function readConfiguredDataMode() {
  const viteMode = typeof import.meta !== "undefined" ? import.meta.env?.VITE_DATA_MODE : null;
  const windowMode = typeof window !== "undefined" ? window.__ASD_DATA_MODE__ : null;
  return windowMode || viteMode || getDefaultDataMode();
}

export function normalizeDataMode(mode) {
  return DATA_MODES.includes(mode) ? mode : "mock";
}

export const DATA_MODE = normalizeDataMode(readConfiguredDataMode());

function readConfiguredFileStorageMode() {
  const viteMode = typeof import.meta !== "undefined" ? import.meta.env?.VITE_FILE_STORAGE_MODE : null;
  const windowMode = typeof window !== "undefined" ? window.__ASD_FILE_STORAGE_MODE__ : null;
  return windowMode || viteMode || getDefaultFileStorageMode();
}

export function normalizeFileStorageMode(mode) {
  return FILE_STORAGE_MODES.includes(mode) ? mode : "metadata_only";
}

export const FILE_STORAGE_MODE = normalizeFileStorageMode(readConfiguredFileStorageMode());

function readConfiguredProcessingMode() {
  const viteMode = typeof import.meta !== "undefined" ? import.meta.env?.VITE_PROCESSING_MODE : null;
  const windowMode = typeof window !== "undefined" ? window.__ASD_PROCESSING_MODE__ : null;
  return windowMode || viteMode || getDefaultProcessingMode();
}

export function normalizeProcessingMode(mode) {
  return PROCESSING_MODES.includes(mode) ? mode : "mock";
}

export const PROCESSING_MODE = normalizeProcessingMode(readConfiguredProcessingMode());
export const PROCESSING_API_BASE_URL =
  (typeof import.meta !== "undefined" ? import.meta.env?.VITE_PROCESSING_API_BASE_URL : null) || "";
export const SECURE_UPLOAD_REQUIRED_CONSENT_STATUS = "granted";

function readConfiguredAuthMode() {
  const viteMode = typeof import.meta !== "undefined" ? import.meta.env?.VITE_AUTH_MODE : null;
  const windowMode = typeof window !== "undefined" ? window.__ASD_AUTH_MODE__ : null;
  return windowMode || viteMode || getDefaultAuthMode();
}

export function normalizeAuthMode(mode) {
  return AUTH_MODES.includes(mode) ? mode : "mock";
}

export const AUTH_MODE = normalizeAuthMode(readConfiguredAuthMode());
export const AUTH_API_BASE_URL =
  (typeof import.meta !== "undefined" ? import.meta.env?.VITE_AUTH_API_BASE_URL : null) ||
  PROCESSING_API_BASE_URL;
export const MAX_FILE_SIZE_MB = 250;
export const ALLOWED_FILE_TYPES = ["wav", "mp3", "m4a", "mp4", "mov"];
export const ALLOWED_TRANSCRIPT_FILE_TYPES = ["cha"];
export const SAFETY_DISCLAIMER =
  "This system is a clinical decision-support prototype. It does not diagnose ASD and does not replace qualified clinical judgment.";

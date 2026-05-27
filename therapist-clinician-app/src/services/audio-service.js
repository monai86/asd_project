import { store } from "../store/state.js";
import { createAudioFile } from "@shared/models";
import { addAudit } from "./audit-service.js";
import { updateSessionStatus } from "./session-service.js";
import { ALLOWED_FILE_TYPES, MAX_FILE_SIZE_MB } from "../constants.js";

export function validateAudioFile(file) {
  const ext = file.name.split(".").pop().toLowerCase();
  if (!ALLOWED_FILE_TYPES.includes(ext)) {
    return { valid: false, error: `Invalid file type: .${ext}. Allowed: ${ALLOWED_FILE_TYPES.join(", ")}` };
  }

  const sizeMb = file.size / 1024 / 1024;
  if (sizeMb > MAX_FILE_SIZE_MB) {
    return { valid: false, error: `File size (${sizeMb.toFixed(1)}MB) exceeds limit of ${MAX_FILE_SIZE_MB}MB` };
  }

  return { valid: true };
}

export function buildStoredFilename(caseId, sessionId, audioFileId, ext) {
  return `${caseId}_${sessionId}_${audioFileId}.${ext}`;
}

export function uploadSessionAudio(file, sessionId, caseId) {
  const { currentUser, audioFiles } = store.getState();
  if (!currentUser) throw new Error("Authentication required");

  const validation = validateAudioFile(file);
  if (!validation.valid) {
    throw new Error(validation.error);
  }

  const audioId = `AUDIO-${String(audioFiles.length + 1).padStart(3, "0")}`;
  const ext = file.name.split(".").pop().toLowerCase();
  const storedName = buildStoredFilename(caseId, sessionId, audioId, ext);

  const newAudio = createAudioFile({
    audio_file_id: audioId,
    session_id: sessionId,
    case_id: caseId,
    owner_user_id: currentUser.user_id,
    original_filename: file.name,
    stored_filename: storedName,
    file_type: ext,
    file_size: file.size,
    duration_seconds: 120, // Mock duration
    processing_status: "completed"
  });

  store.setState({
    audioFiles: [...audioFiles, newAudio]
  });

  updateSessionStatus(sessionId, {
    audio_file_id: audioId,
    processing_status: "uploaded"
  });

  addAudit(
    "audio_upload",
    "AudioFile",
    audioId,
    `Uploaded file metadata for ${file.name}. No file bytes are persisted (Metadata-only mock upload).`
  );

  return newAudio;
}

import { store } from "../store/state.js";
import { createAudioFile } from "@shared/models";
import { addAudit } from "./audit-service.js";
import { getVisibleSessions, updateSessionStatus } from "./session-service.js";
import {
  fileStorageAdapter,
  getFileStorageLabel
} from "../storage/file-storage-adapter.js";
import { SECURE_UPLOAD_REQUIRED_CONSENT_STATUS } from "../constants.js";
import { createSecureAudioUploadIntent, buildSecureUploadIntentPayload } from "./audio-processing-api.js";
import { api } from "./api-client.js";
import { getSecureMediaUploadSurface } from "./platform-service.js";

export function validateAudioFile(file) {
  return fileStorageAdapter.validateFile(file);
}

export function buildStoredFilename(caseId, sessionId, audioFileId, ext) {
  return fileStorageAdapter.buildStoredFilename({
    case_id: caseId,
    session_id: sessionId,
    audio_file_id: audioFileId,
    extension: ext
  });
}

export function getAudioFileUrl(audioFileId) {
  const url = fileStorageAdapter.getFileUrl(audioFileId);
  if (url) return url;
  const state = store.getState();
  const audioFile = state.audioFiles.find(a => a.audio_file_id === audioFileId);
  if (audioFile && state.audioUrls[audioFile.session_id]) {
    return state.audioUrls[audioFile.session_id];
  }
  return null;
}

export function getAudioFileMetadata(audioFileId) {
  return fileStorageAdapter.getFileMetadata(audioFileId) || store.getState().audioFiles.find(file => file.audio_file_id === audioFileId) || null;
}

export function hasSecureAudioConsent(childCase) {
  return childCase?.consent_status === SECURE_UPLOAD_REQUIRED_CONSENT_STATUS;
}

export function assertSecureAudioConsent(childCase) {
  if (!hasSecureAudioConsent(childCase)) {
    throw new Error("Guardian consent must be granted before secure audio upload or backend audio processing.");
  }
}

export function deleteAudioFile(audioFileId) {
  const { audioFiles, sessions } = store.getState();
  const targetAudio = audioFiles.find(file => file.audio_file_id === audioFileId);
  if (!targetAudio) return false;

  fileStorageAdapter.deleteFile(audioFileId);
  store.setState({
    audioFiles: audioFiles.filter(file => file.audio_file_id !== audioFileId),
    sessions: sessions.map(session =>
      session.audio_file_id === audioFileId
        ? { ...session, audio_file_id: null, processing_status: "not_started", updated_at: new Date().toISOString() }
        : session
    )
  });
  addAudit("audio_deleted", "AudioFile", audioFileId, `Deleted audio metadata for ${targetAudio.original_filename}.`);
  return true;
}

export function uploadSessionAudio(file, sessionId, caseId) {
  const { currentUser, audioFiles, cases } = store.getState();
  if (!currentUser) throw new Error("Authentication required");
  const targetSession = getVisibleSessions().find(session => session.session_id === sessionId && session.case_id === caseId);
  if (!targetSession) throw new Error("Session access denied");
  const childCase = cases.find(item => item.case_id === caseId);

  if (
    fileStorageAdapter.mode === "secure_backend" ||
    fileStorageAdapter.mode === "supabase_storage" ||
    fileStorageAdapter.mode === "backend_placeholder"
  ) {
    assertSecureAudioConsent(childCase);
  }

  const validation = validateAudioFile(file);
  if (!validation.valid) {
    throw new Error(validation.error);
  }

  const audioId = `AUDIO-${String(audioFiles.length + 1).padStart(3, "0")}`;
  const ext = validation.extension;
  const storedName = buildStoredFilename(caseId, sessionId, audioId, ext);

  const audioMetadata = createAudioFile({
    audio_file_id: audioId,
    session_id: sessionId,
    case_id: caseId,
    owner_user_id: targetSession.owner_user_id,
    original_filename: file.name,
    stored_filename: storedName,
    file_type: ext,
    file_size: file.size,
    duration_seconds: 120, // Mock duration
    processing_status: "completed",
    storage_mode: fileStorageAdapter.mode
  });
  const newAudio = fileStorageAdapter.saveFile(file, audioMetadata);

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
    `Uploaded file metadata for ${file.name}. ${getFileStorageLabel(newAudio.storage_mode)}`
  );

  return newAudio;
}

export async function requestSecureUploadIntent(file, sessionId, caseId) {
  const { cases, dataMode } = store.getState();
  const childCase = cases.find(item => item.case_id === caseId);
  assertSecureAudioConsent(childCase);

  let intent;
  if (dataMode === "api") {
    const payload = buildSecureUploadIntentPayload(file);
    intent = await api.post(`/api/sessions/${sessionId}/audio/upload-intent`, payload);
  } else {
    intent = await createSecureAudioUploadIntent(sessionId, file);
  }

  addAudit(
    "secure_upload_intent_requested",
    "Session",
    sessionId,
    intent.status === "not_configured"
      ? intent.message
      : "Requested secure signed-upload URL for private audio storage."
  );
  return intent;
}

async function putFileToSignedUrl(file, intent) {
  const signedUrl = intent?.upload?.signed_upload_url || intent?.upload?.url;
  if (!signedUrl) {
    throw new Error("Secure upload intent did not include a signed upload URL.");
  }
  const response = await fetch(signedUrl, {
    method: intent.upload?.method || "PUT",
    headers: {
      "Content-Type": file.type || "application/octet-stream",
      ...(intent.upload?.headers || {})
    },
    body: file
  });
  if (!response.ok) {
    throw new Error(`Secure media upload failed with status ${response.status}.`);
  }
  return {
    uploaded: true,
    surface: getSecureMediaUploadSurface(),
    status: response.status
  };
}

export async function uploadSecureAudioFile(file, sessionId, caseId) {
  const intent = await requestSecureUploadIntent(file, sessionId, caseId);
  if (intent.status === "not_configured") {
    return { intent, upload: null, audioFile: null };
  }
  const uploadResult = await putFileToSignedUrl(file, intent);
  const audioFile = applySecureUploadIntent(intent);
  addAudit(
    "secure_media_uploaded",
    "AudioFile",
    audioFile?.audio_file_id || intent.audio_file?.audio_file_id || sessionId,
    `Secure media upload completed through ${uploadResult.surface}. Permanent storage keys were not exposed to the client.`
  );
  return { intent, upload: uploadResult, audioFile };
}

export function applySecureUploadIntent(intent) {
  const { audioFiles } = store.getState();
  if (!intent?.audio_file) return null;
  const nextAudio = {
    ...intent.audio_file,
    signed_upload_required: true,
    signed_upload_url: intent.upload?.signed_upload_url || intent.upload?.url || null,
    signed_upload_expires_in_seconds: intent.upload?.expires_in_seconds || null,
    storage_provider: intent.upload?.storage_provider || "supabase",
    exposes_permanent_storage_key: Boolean(intent.file_object?.storage_key)
  };
  store.setState({
    audioFiles: [
      ...audioFiles.filter(item => item.audio_file_id !== nextAudio.audio_file_id),
      nextAudio
    ]
  });
  updateSessionStatus(nextAudio.session_id, {
    audio_file_id: nextAudio.audio_file_id,
    processing_status: "uploaded"
  });
  return nextAudio;
}

export { getFileStorageLabel };

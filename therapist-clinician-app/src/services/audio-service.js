import { store } from "../store/state.js";
import { createAudioFile } from "@shared/models";
import { addAudit } from "./audit-service.js";
import { getVisibleSessions, updateSessionStatus } from "./session-service.js";
import {
  fileStorageAdapter,
  getFileStorageLabel
} from "../storage/file-storage-adapter.js";

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
  return fileStorageAdapter.getFileUrl(audioFileId);
}

export function getAudioFileMetadata(audioFileId) {
  return fileStorageAdapter.getFileMetadata(audioFileId) || store.getState().audioFiles.find(file => file.audio_file_id === audioFileId) || null;
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
  const { currentUser, audioFiles } = store.getState();
  if (!currentUser) throw new Error("Authentication required");
  const targetSession = getVisibleSessions().find(session => session.session_id === sessionId && session.case_id === caseId);
  if (!targetSession) throw new Error("Session access denied");

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

export { getFileStorageLabel };

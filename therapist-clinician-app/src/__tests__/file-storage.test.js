import { beforeEach, describe, expect, it, vi } from "vitest";
import { createAudioFile } from "@shared/models";
import { store } from "../store/state.js";
import {
  applySecureUploadIntent,
  assertSecureAudioConsent,
  hasSecureAudioConsent,
  uploadSessionAudio
} from "../services/audio-service.js";
import {
  FileStorageAdapter,
  getFileStorageLabel
} from "../storage/file-storage-adapter.js";
import { renderSessionView } from "../views/session-view.js";

function testFile(name, size = 1024) {
  return { name, size };
}

describe("file storage adapter", () => {
  it.each(["wav", "mp3", "m4a", "mp4", "mov"])("allows %s files", extension => {
    const adapter = new FileStorageAdapter();
    expect(adapter.validateFile(testFile(`sample.${extension}`))).toEqual({
      valid: true,
      extension
    });
  });

  it("rejects unsupported file types with a friendly message", () => {
    const adapter = new FileStorageAdapter();
    const result = adapter.validateFile(testFile("child-name.pdf"));

    expect(result.valid).toBe(false);
    expect(result.error).toContain("Unsupported file type");
    expect(result.error).toContain("wav, mp3, m4a, mp4, mov");
  });

  it("rejects files larger than the configured maximum size", () => {
    const adapter = new FileStorageAdapter({ maxFileSizeMb: 1 });
    const result = adapter.validateFile(testFile("sample.wav", 2 * 1024 * 1024));

    expect(result.valid).toBe(false);
    expect(result.error).toContain("maximum allowed size is 1 MB");
  });

  it("generates anonymized stored filenames from case, session, and audio IDs only", () => {
    const adapter = new FileStorageAdapter();
    const filename = adapter.buildStoredFilename({
      case_id: "CASE-001",
      session_id: "SESSION-001",
      audio_file_id: "AUDIO-001",
      extension: "wav"
    });

    expect(filename).toBe("CASE-001_SESSION-001_AUDIO-001.wav");
    expect(filename).not.toContain("child");
    expect(filename).not.toContain("Jane");
  });

  it("creates temporary browser preview URLs without storing them in metadata", () => {
    const createObjectUrl = vi.fn(() => "blob:preview-url");
    const revokeObjectUrl = vi.fn();
    const adapter = new FileStorageAdapter({
      mode: "browser_preview",
      createObjectUrl,
      revokeObjectUrl
    });
    const metadata = createAudioFile({
      audio_file_id: "AUDIO-001",
      session_id: "SESSION-001",
      case_id: "CASE-001",
      owner_user_id: "therapist_a",
      original_filename: "sample.wav",
      stored_filename: "CASE-001_SESSION-001_AUDIO-001.wav",
      file_type: "wav",
      file_size: 1024
    });

    const saved = adapter.saveFile(testFile("sample.wav"), metadata);

    expect(saved.storage_mode).toBe("browser_preview");
    expect(saved.file_url).toBeUndefined();
    expect(adapter.getFileUrl("AUDIO-001")).toBe("blob:preview-url");
    expect(adapter.getFileMetadata("AUDIO-001")).toEqual(saved);
    expect(adapter.deleteFile("AUDIO-001")).toBe(true);
    expect(revokeObjectUrl).toHaveBeenCalledWith("blob:preview-url");
  });

  it("marks backend placeholder metadata without saving file bytes", () => {
    const adapter = new FileStorageAdapter({ mode: "backend_placeholder" });
    const metadata = createAudioFile({
      audio_file_id: "AUDIO-002",
      session_id: "SESSION-002",
      case_id: "CASE-002",
      owner_user_id: "therapist_a",
      original_filename: "sample.mp4",
      stored_filename: "CASE-002_SESSION-002_AUDIO-002.mp4",
      file_type: "mp4",
      file_size: 1024
    });

    const saved = adapter.saveFile(testFile("sample.mp4"), metadata);

    expect(saved.storage_mode).toBe("backend_placeholder");
    expect(saved.processing_status).toBe("pending");
    expect(adapter.getFileUrl("AUDIO-002")).toBeNull();
  });

  it("marks secure backend metadata as signed-upload only", () => {
    const adapter = new FileStorageAdapter({ mode: "secure_backend" });
    const metadata = createAudioFile({
      audio_file_id: "AUDIO-003",
      session_id: "SESSION-003",
      case_id: "CASE-003",
      owner_user_id: "therapist_a",
      original_filename: "sample.wav",
      stored_filename: "CASE-003_SESSION-003_AUDIO-003.wav",
      file_type: "wav",
      file_size: 1024
    });

    const saved = adapter.saveFile(testFile("sample.wav"), metadata);

    expect(saved.storage_mode).toBe("secure_backend");
    expect(saved.signed_upload_required).toBe(true);
    expect(adapter.getFileUrl("AUDIO-003")).toBeNull();
  });

  it("marks Supabase Storage metadata as signed-upload only", () => {
    const adapter = new FileStorageAdapter({ mode: "supabase_storage" });
    const metadata = createAudioFile({
      audio_file_id: "AUDIO-004",
      session_id: "SESSION-004",
      case_id: "CASE-004",
      owner_user_id: "therapist_a",
      original_filename: "sample.wav",
      stored_filename: "CASE-004_SESSION-004_AUDIO-004.wav",
      file_type: "wav",
      file_size: 1024
    });

    const saved = adapter.saveFile(testFile("sample.wav"), metadata);

    expect(saved.storage_mode).toBe("supabase_storage");
    expect(saved.signed_upload_required).toBe(true);
    expect(adapter.getFileUrl("AUDIO-004")).toBeNull();
  });

  it("exposes storage mode labels for the UI", () => {
    expect(getFileStorageLabel("metadata_only")).toBe("Metadata-only upload: no audio/video bytes are stored.");
    expect(getFileStorageLabel("browser_preview")).toBe("Temporary local preview only.");
    expect(getFileStorageLabel("backend_placeholder")).toBe("Backend storage adapter not configured yet.");
    expect(getFileStorageLabel("secure_backend")).toBe("Secure backend storage: encrypted private object storage with signed upload URLs.");
    expect(getFileStorageLabel("supabase_storage")).toBe("Supabase Storage: encrypted private object storage with signed upload URLs.");
  });
});

describe("secure audio consent gate", () => {
  it("requires granted consent before secure audio upload", () => {
    expect(hasSecureAudioConsent({ consent_status: "granted" })).toBe(true);
    expect(hasSecureAudioConsent({ consent_status: "pending" })).toBe(false);
    expect(() => assertSecureAudioConsent({ consent_status: "pending" })).toThrow("Guardian consent");
  });
});

describe("audio upload metadata integration", () => {
  beforeEach(() => {
    store.persistenceAdapter = null;
    store.setState({
      currentUser: { user_id: "therapist_a", role: "therapist", name: "Therapist A" },
      cases: [{ case_id: "CASE-001", owner_user_id: "therapist_a", anonymized_child_code: "CHI-A", display_label: "Case A" }],
      sessions: [{
        session_id: "SESSION-001",
        case_id: "CASE-001",
        owner_user_id: "therapist_a",
        session_date: "2026-05-20",
        session_type: "free_play",
        processing_status: "not_started"
      }],
      selectedSessionId: "SESSION-001",
      audioFiles: [],
      transcripts: {},
      auditLogs: []
    });
  });

  it("links uploaded metadata to the correct case, session, and owner", () => {
    const audio = uploadSessionAudio(testFile("caregiver_phone_sample.wav", 2048), "SESSION-001", "CASE-001");

    expect(audio).toMatchObject({
      audio_file_id: "AUDIO-001",
      owner_user_id: "therapist_a",
      case_id: "CASE-001",
      session_id: "SESSION-001",
      original_filename: "caregiver_phone_sample.wav",
      stored_filename: "CASE-001_SESSION-001_AUDIO-001.wav",
      file_type: "wav",
      file_size: 2048,
      storage_mode: "metadata_only"
    });
    expect(store.getState().sessions[0].audio_file_id).toBe("AUDIO-001");
  });

  it("shows the active storage mode label in the session UI", () => {
    const html = renderSessionView();

    expect(html).toContain("Metadata-only upload: no audio/video bytes are stored.");
  });

  it("applies secure upload intent metadata without storing permanent object keys", () => {
    const audio = applySecureUploadIntent({
      audio_file: {
        audio_file_id: "AUDIO-SECURE-001",
        session_id: "SESSION-001",
        case_id: "CASE-001",
        owner_user_id: "therapist_a",
        original_filename: "sample.wav",
        stored_filename: "CASE-001_SESSION-001_AUDIO-SECURE-001.wav",
        file_type: "wav",
        file_size: 2048,
        storage_mode: "secure_private"
      },
      file_object: {
        file_object_id: "FILEOBJ-001",
        encryption_status: "required"
      },
      upload: {
        signed_upload_url: "https://private-storage.local/upload/FILEOBJ-001",
        expires_in_seconds: 900,
        storage_provider: "supabase"
      }
    });

    expect(audio).toMatchObject({
      audio_file_id: "AUDIO-SECURE-001",
      signed_upload_required: true,
      signed_upload_expires_in_seconds: 900,
      storage_provider: "supabase",
      exposes_permanent_storage_key: false
    });
    expect(store.getState().sessions[0].audio_file_id).toBe("AUDIO-SECURE-001");
  });
});

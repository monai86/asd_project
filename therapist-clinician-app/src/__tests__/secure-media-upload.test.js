import { beforeEach, describe, expect, it, vi } from "vitest";
import { store } from "../store/state.js";
import { uploadSecureAudioFile } from "../services/audio-service.js";
import * as apiClient from "../services/api-client.js";

describe("secure media upload", () => {
  beforeEach(() => {
    store.setState({
      currentUser: { user_id: "user-1", role: "therapist" },
      dataMode: "api",
      cases: [{ case_id: "CASE-1", consent_status: "granted" }],
      sessions: [{ session_id: "SESSION-1", case_id: "CASE-1", owner_user_id: "user-1" }],
      audioFiles: [],
      auditLogs: []
    });
  });

  it("uploads to the signed URL and stores redacted client metadata", async () => {
    const putFetch = vi.fn(async () => ({ ok: true, status: 200 }));
    globalThis.fetch = putFetch;
    vi.spyOn(apiClient.api, "post").mockResolvedValue({
      audio_file: {
        audio_file_id: "AUDIO-1",
        session_id: "SESSION-1",
        case_id: "CASE-1",
        owner_user_id: "user-1",
        original_filename: "sample.wav",
        storage_mode: "supabase_storage"
      },
      upload: {
        signed_upload_url: "https://storage.example/upload",
        method: "PUT",
        expires_in_seconds: 300,
        storage_provider: "supabase"
      },
      file_object: {
        file_object_id: "FILE-1",
        storage_key: undefined,
        encryption_status: "encrypted"
      }
    });

    const file = new File(["audio-bytes"], "sample.wav", { type: "audio/wav" });
    const result = await uploadSecureAudioFile(file, "SESSION-1", "CASE-1");

    expect(result.upload.uploaded).toBe(true);
    expect(putFetch).toHaveBeenCalledWith(
      "https://storage.example/upload",
      expect.objectContaining({ method: "PUT", body: file })
    );
    expect(store.getState().audioFiles[0].exposes_permanent_storage_key).toBe(false);
  });
});

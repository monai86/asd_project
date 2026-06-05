import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  FileStorageAdapter,
  createFileStorageAdapter,
  FILE_STORAGE_LABELS
} from "../storage/file-storage-adapter.js";

describe("FileStorageAdapter", () => {
  let adapter;

  beforeEach(() => {
    adapter = new FileStorageAdapter({
      mode: "supabase_storage",
      maxFileSizeMb: 250,
      allowedFileTypes: ["wav", "mp3", "m4a", "mp4", "mov"],
      createObjectUrl: vi.fn(() => "blob:mock-url"),
      revokeObjectUrl: vi.fn()
    });
  });

  describe("validateFile", () => {
    it("rejects files with unsupported extension", () => {
      const file = { name: "test.exe", size: 1024 };
      const result = adapter.validateFile(file);
      expect(result.valid).toBe(false);
      expect(result.error).toContain("Unsupported");
    });

    it("rejects oversized files", () => {
      const file = { name: "test.wav", size: 300 * 1024 * 1024 };
      const result = adapter.validateFile(file);
      expect(result.valid).toBe(false);
      expect(result.error).toContain("maximum allowed size");
    });

    it("accepts valid audio files", () => {
      const file = { name: "recording.wav", size: 5 * 1024 * 1024 };
      const result = adapter.validateFile(file);
      expect(result.valid).toBe(true);
      expect(result.extension).toBe("wav");
    });

    it("rejects missing file", () => {
      const result = adapter.validateFile(null);
      expect(result.valid).toBe(false);
    });
  });

  describe("saveFile in supabase_storage mode", () => {
    it("returns metadata with signed_upload_required=true", () => {
      const file = { name: "test.wav", size: 1024, type: "audio/wav" };
      const metadata = {
        audio_file_id: "AUDIO-001",
        session_id: "sess-001",
        case_id: "case-001"
      };
      const result = adapter.saveFile(file, metadata);
      expect(result.signed_upload_required).toBe(true);
      expect(result.storage_mode).toBe("supabase_storage");
      expect(result.processing_status).toBe("pending");
    });
  });

  describe("saveFile in browser_preview mode", () => {
    it("creates object URL for preview", () => {
      const previewAdapter = new FileStorageAdapter({
        mode: "browser_preview",
        createObjectUrl: vi.fn(() => "blob:preview-url"),
        revokeObjectUrl: vi.fn()
      });
      const file = { name: "test.wav", size: 1024 };
      const metadata = { audio_file_id: "AUDIO-001" };
      const result = previewAdapter.saveFile(file, metadata);
      expect(result.storage_mode).toBe("browser_preview");
      expect(previewAdapter.getFileUrl("AUDIO-001")).toBe("blob:preview-url");
    });
  });

  describe("uploadToSignedUrl", () => {
    it("makes PUT request with correct headers", async () => {
      const mockFetch = vi.fn(() =>
        Promise.resolve({ ok: true, status: 200 })
      );
      globalThis.fetch = mockFetch;

      const file = new Blob(["audio-data"], { type: "audio/wav" });
      const signedUrl = "https://storage.supabase.co/upload/audio/test.wav";
      const headers = { "x-amz-server-side-encryption": "AES256" };

      const result = await adapter.uploadToSignedUrl(file, signedUrl, headers);

      expect(mockFetch).toHaveBeenCalledWith(signedUrl, {
        method: "PUT",
        headers: {
          "x-amz-server-side-encryption": "AES256",
          "Content-Type": "audio/wav"
        },
        body: file
      });
      expect(result.ok).toBe(true);
      expect(result.status).toBe(200);
    });

    it("throws on non-ok response", async () => {
      globalThis.fetch = vi.fn(() =>
        Promise.resolve({
          ok: false,
          status: 403,
          text: () => Promise.resolve("Forbidden")
        })
      );

      const file = new Blob(["data"]);
      await expect(
        adapter.uploadToSignedUrl(file, "https://example.com/upload")
      ).rejects.toThrow("Upload failed (403)");
    });

    it("uses application/octet-stream as fallback content type", async () => {
      const mockFetch = vi.fn(() =>
        Promise.resolve({ ok: true, status: 200 })
      );
      globalThis.fetch = mockFetch;

      const file = new Blob(["data"]);
      Object.defineProperty(file, "type", { value: "" });
      await adapter.uploadToSignedUrl(file, "https://example.com/upload");

      const callArgs = mockFetch.mock.calls[0][1];
      expect(callArgs.headers["Content-Type"]).toBe("application/octet-stream");
    });
  });

  describe("confirmUpload", () => {
    it("updates metadata to confirmed state", () => {
      const file = { name: "test.wav", size: 1024 };
      const metadata = { audio_file_id: "AUDIO-001" };
      adapter.saveFile(file, metadata);

      const confirmed = adapter.confirmUpload("AUDIO-001");
      expect(confirmed).not.toBeNull();
      expect(confirmed.upload_pending).toBe(false);
      expect(confirmed.processing_status).toBe("uploaded");
    });

    it("returns null for unknown audio file id", () => {
      const result = adapter.confirmUpload("nonexistent");
      expect(result).toBeNull();
    });
  });

  describe("deleteFile", () => {
    it("removes preview URL and metadata", () => {
      const previewAdapter = new FileStorageAdapter({
        mode: "browser_preview",
        createObjectUrl: vi.fn(() => "blob:preview-url"),
        revokeObjectUrl: vi.fn()
      });
      const file = { name: "test.wav", size: 1024 };
      previewAdapter.saveFile(file, { audio_file_id: "AUDIO-001" });

      expect(previewAdapter.getFileUrl("AUDIO-001")).toBe("blob:preview-url");
      previewAdapter.deleteFile("AUDIO-001");
      expect(previewAdapter.getFileUrl("AUDIO-001")).toBeNull();
      expect(previewAdapter.getFileMetadata("AUDIO-001")).toBeNull();
    });
  });

  describe("labels", () => {
    it("has correct label for supabase_storage mode", () => {
      expect(adapter.label).toBe(FILE_STORAGE_LABELS.supabase_storage);
    });
  });
});

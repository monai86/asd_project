import {
  ALLOWED_FILE_TYPES,
  FILE_STORAGE_MODE,
  MAX_FILE_SIZE_MB,
  normalizeFileStorageMode
} from "../constants.js";

export const FILE_STORAGE_LABELS = {
  metadata_only: "Metadata-only upload: no audio/video bytes are stored.",
  browser_preview: "Temporary local preview only.",
  backend_placeholder: "Backend storage adapter not configured yet.",
  secure_backend: "Secure backend storage: encrypted private object storage with signed upload URLs.",
  supabase_storage: "Supabase Storage: encrypted private object storage with signed upload URLs."
};

function getExtension(filename = "") {
  const parts = filename.split(".");
  return parts.length > 1 ? parts.pop().toLowerCase() : "";
}

function defaultUrlFactory(file) {
  if (typeof URL !== "undefined" && typeof URL.createObjectURL === "function") {
    return URL.createObjectURL(file);
  }
  return null;
}

function defaultUrlRevoker(url) {
  if (typeof URL !== "undefined" && typeof URL.revokeObjectURL === "function") {
    URL.revokeObjectURL(url);
  }
}

export class FileStorageAdapter {
  constructor({
    mode = FILE_STORAGE_MODE,
    maxFileSizeMb = MAX_FILE_SIZE_MB,
    allowedFileTypes = ALLOWED_FILE_TYPES,
    createObjectUrl = defaultUrlFactory,
    revokeObjectUrl = defaultUrlRevoker
  } = {}) {
    this.mode = normalizeFileStorageMode(mode);
    this.maxFileSizeMb = maxFileSizeMb;
    this.allowedFileTypes = allowedFileTypes;
    this.createObjectUrl = createObjectUrl;
    this.revokeObjectUrl = revokeObjectUrl;
    this.previewUrls = new Map();
    this.metadataByAudioFileId = new Map();
  }

  get label() {
    return FILE_STORAGE_LABELS[this.mode];
  }

  validateFile(file) {
    if (!file?.name) {
      return { valid: false, error: "Choose an audio or video file before uploading." };
    }

    const extension = getExtension(file.name);
    if (!this.allowedFileTypes.includes(extension)) {
      return {
        valid: false,
        error: `Unsupported file type .${extension || "unknown"}. Please upload ${this.allowedFileTypes.join(", ")}.`
      };
    }

    const sizeMb = (file.size || 0) / 1024 / 1024;
    if (sizeMb > this.maxFileSizeMb) {
      return {
        valid: false,
        error: `File is ${sizeMb.toFixed(1)} MB. The maximum allowed size is ${this.maxFileSizeMb} MB.`
      };
    }

    return { valid: true, extension };
  }

  buildStoredFilename({ case_id, session_id, audio_file_id, extension }) {
    return `${case_id}_${session_id}_${audio_file_id}.${extension.toLowerCase()}`;
  }

  saveFile(file, metadata) {
    if (this.mode === "backend_placeholder" || this.mode === "secure_backend" || this.mode === "supabase_storage") {
      const nextMetadata = {
        ...metadata,
        storage_mode: this.mode,
        processing_status: "pending",
        signed_upload_required: this.mode === "secure_backend" || this.mode === "supabase_storage"
      };
      this.metadataByAudioFileId.set(metadata.audio_file_id, nextMetadata);
      return nextMetadata;
    }

    const nextMetadata = {
      ...metadata,
      storage_mode: this.mode
    };

    if (this.mode === "browser_preview") {
      const url = this.createObjectUrl(file);
      if (url) {
        this.previewUrls.set(metadata.audio_file_id, url);
      }
    }

    this.metadataByAudioFileId.set(metadata.audio_file_id, nextMetadata);
    return nextMetadata;
  }

  getFileUrl(audio_file_id) {
    return this.previewUrls.get(audio_file_id) || null;
  }

  getFileMetadata(audio_file_id) {
    return this.metadataByAudioFileId.get(audio_file_id) || null;
  }

  deleteFile(audio_file_id) {
    const url = this.previewUrls.get(audio_file_id);
    if (url) {
      this.revokeObjectUrl(url);
      this.previewUrls.delete(audio_file_id);
    }
    return this.metadataByAudioFileId.delete(audio_file_id);
  }
}

export function createFileStorageAdapter(options = {}) {
  return new FileStorageAdapter(options);
}

export const fileStorageAdapter = createFileStorageAdapter();

export function getFileStorageLabel(mode = FILE_STORAGE_MODE) {
  return FILE_STORAGE_LABELS[normalizeFileStorageMode(mode)];
}

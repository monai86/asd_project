export function createProcessingJob({
  job_id,
  session_id,
  case_id,
  owner_user_id,
  audio_file_id = null,
  job_type = "audio_pipeline",
  status = "queued",
  stage = "queued",
  progress = 0,
  error_code = null,
  error_message = "",
  result_refs = {},
  created_at = new Date().toISOString(),
  updated_at = created_at,
  started_at = null,
  finished_at = null
} = {}) {
  return {
    job_id,
    session_id,
    case_id,
    owner_user_id,
    audio_file_id,
    job_type,
    status,
    stage,
    progress,
    error_code,
    error_message,
    result_refs,
    created_at,
    updated_at,
    started_at,
    finished_at
  };
}

export const PROCESSING_JOB_STAGES = [
  "queued",
  "transcribing",
  "diarizing",
  "chat_formatting",
  "qa_running",
  "features_running",
  "awaiting_review",
  "completed",
  "failed"
];

export function normalizeProcessingJobStage(stage, status = "queued") {
  if (PROCESSING_JOB_STAGES.includes(stage)) return stage;
  if (status === "completed") return "awaiting_review";
  if (status === "failed") return "failed";
  if (status === "processing") return "transcribing";
  return "queued";
}

export function processingJobSessionStatus(job = {}) {
  const stage = normalizeProcessingJobStage(job.stage, job.status);
  if (job.status === "failed" || stage === "failed") return "failed";
  if (stage === "awaiting_review") return "transcript_ready";
  if (stage === "completed") return "completed";
  if (job.status === "queued" || stage === "queued") return "processing_submitted";
  return "processing";
}

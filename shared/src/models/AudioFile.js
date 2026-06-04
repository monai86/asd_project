export function createAudioFile({
  audio_file_id,
  session_id,
  case_id,
  owner_user_id,
  original_filename,
  stored_filename = "",
  file_type,
  file_size = 0,
  duration_seconds = 0,
  upload_time = new Date().toISOString(),
  processing_status = "completed"
}) {
  return {
    audio_file_id,
    session_id,
    case_id,
    owner_user_id,
    original_filename,
    stored_filename,
    file_type,
    file_size,
    duration_seconds,
    upload_time,
    processing_status
  };
}

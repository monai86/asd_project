"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, Pause, Play, RotateCcw, Square, Trash2 } from "lucide-react";

export type RecordingMetadata = {
  recordingStatus: "idle" | "recording" | "paused" | "stopped" | "interrupted" | "error";
  durationSeconds: number;
  mimeType?: string;
  createdAt?: string;
  hasUnsavedRecording: boolean;
  error?: string;
};

type BrowserAudioRecorderProps = {
  initialDurationSeconds: number;
  hadUnsavedRecording: boolean;
  onMetadataChange: (metadata: RecordingMetadata) => void;
  onRecordingReady?: (blob: Blob, metadata: RecordingMetadata) => void;
  onRecordingCleared?: () => void;
};

export function BrowserAudioRecorder({
  initialDurationSeconds,
  hadUnsavedRecording,
  onMetadataChange,
  onRecordingReady,
  onRecordingCleared
}: BrowserAudioRecorderProps) {
  const [status, setStatus] = useState<RecordingMetadata["recordingStatus"]>("idle");
  const [durationSeconds, setDurationSeconds] = useState(initialDurationSeconds);
  const [audioUrl, setAudioUrl] = useState("");
  const [error, setError] = useState("");
  const [privacyNotice, setPrivacyNotice] = useState(hadUnsavedRecording);
  const [amplitudes, setAmplitudes] = useState<number[]>(() => Array.from({ length: 24 }, () => 8));
  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioBlobRef = useRef<Blob | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | undefined>(undefined);
  const animationRef = useRef<number | undefined>(undefined);
  const audioContextRef = useRef<AudioContext | null>(null);
  const trackEndedHandlerRef = useRef<(() => void) | null>(null);
  const durationRef = useRef(initialDurationSeconds);
  const statusRef = useRef(status);
  const audioUrlRef = useRef("");
  const createdAtRef = useRef<string | undefined>(undefined);
  const mimeTypeRef = useRef<string | undefined>(undefined);

  useEffect(() => {
    statusRef.current = status;
  }, [status]);

  useEffect(() => {
    durationRef.current = durationSeconds;
  }, [durationSeconds]);

  useEffect(() => {
    if (statusRef.current !== "idle" || audioUrlRef.current) return;
    setDurationSeconds(initialDurationSeconds);
    durationRef.current = initialDurationSeconds;
  }, [initialDurationSeconds]);

  useEffect(() => {
    if (hadUnsavedRecording) setPrivacyNotice(true);
  }, [hadUnsavedRecording]);

  useEffect(() => () => {
    clearTimer();
    stopVisualization();
    stopStream();
    revokeAudioUrl();
  }, []);

  async function startRecording() {
    setError("");
    setPrivacyNotice(false);
    revokeAudioUrl();
    setDurationSeconds(0);
    durationRef.current = 0;

    if (typeof window === "undefined" || typeof window.MediaRecorder === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      fail("Audio recording is not supported in this browser.");
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      chunksRef.current = [];
      const mimeType = selectMimeType();
      const recorder = mimeType ? new window.MediaRecorder(stream, { mimeType }) : new window.MediaRecorder(stream);
      recorderRef.current = recorder;
      const createdAt = new Date().toISOString();
      createdAtRef.current = createdAt;
      mimeTypeRef.current = recorder.mimeType || mimeType || "audio/webm";

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.onerror = () => interruptRecording("Recording was interrupted. Please record again.");
      recorder.onstop = () => finalizeRecording(recorder.mimeType || mimeType || "audio/webm", createdAt);
      attachTrackEndedHandler(stream);
      recorder.start(250);
      setStatus("recording");
      statusRef.current = "recording";
      startTimer();
      startVisualization(stream);
      onMetadataChange({
        recordingStatus: "recording",
        durationSeconds: 0,
        mimeType: recorder.mimeType || mimeType,
        createdAt,
        hasUnsavedRecording: true
      });
    } catch (cause) {
      const message = cause instanceof DOMException && (cause.name === "NotAllowedError" || cause.name === "SecurityError")
        ? "Microphone permission was denied."
        : "Microphone could not be started. Check the device and try again.";
      fail(message);
    }
  }

  function pauseRecording() {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state !== "recording") return;
    recorder.pause();
    clearTimer();
    setStatus("paused");
    statusRef.current = "paused";
    onMetadataChange(currentMetadata("paused", true));
  }

  function resumeRecording() {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state !== "paused") return;
    recorder.resume();
    setStatus("recording");
    statusRef.current = "recording";
    startTimer();
    onMetadataChange(currentMetadata("recording", true));
  }

  function stopRecording() {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") return;
    clearTimer();
    stopVisualization();
    recorder.stop();
  }

  function deleteRecording() {
    resetRecording();
    onRecordingCleared?.();
    onMetadataChange({
      recordingStatus: "idle",
      durationSeconds: 0,
      hasUnsavedRecording: false
    });
  }

  async function rerecord() {
    resetRecording();
    await startRecording();
  }

  function resetRecording() {
    clearTimer();
    stopVisualization();
    stopStream();
    recorderRef.current = null;
    chunksRef.current = [];
    audioBlobRef.current = null;
    revokeAudioUrl();
    setDurationSeconds(0);
    durationRef.current = 0;
    setStatus("idle");
    statusRef.current = "idle";
    setError("");
    setPrivacyNotice(false);
    createdAtRef.current = undefined;
    mimeTypeRef.current = undefined;
  }

  function finalizeRecording(mimeType: string, createdAt: string) {
    clearTimer();
    stopVisualization();
    stopStream();
    const blob = new Blob(chunksRef.current, { type: mimeType });
    chunksRef.current = [];
    recorderRef.current = null;
    if (blob.size === 0) {
      fail("The recording was empty. Please record again.");
      return;
    }
    audioBlobRef.current = blob;
    const url = URL.createObjectURL(blob);
    audioUrlRef.current = url;
    setAudioUrl(url);
    setStatus("stopped");
    statusRef.current = "stopped";
    const metadata: RecordingMetadata = {
      recordingStatus: "stopped",
      durationSeconds: durationRef.current,
      mimeType,
      createdAt,
      hasUnsavedRecording: true
    };
    onMetadataChange(metadata);
    onRecordingReady?.(blob, metadata);
  }

  function interruptRecording(message: string) {
    if (statusRef.current !== "recording" && statusRef.current !== "paused") return;
    clearTimer();
    stopVisualization();
    stopStream();
    recorderRef.current = null;
    chunksRef.current = [];
    setStatus("interrupted");
    statusRef.current = "interrupted";
    setError(message);
    onMetadataChange({
      recordingStatus: "interrupted",
      durationSeconds: durationRef.current,
      hasUnsavedRecording: false,
      error: message
    });
  }

  function fail(message: string) {
    clearTimer();
    stopVisualization();
    stopStream();
    setStatus("error");
    statusRef.current = "error";
    setError(message);
    onMetadataChange({
      recordingStatus: "error",
      durationSeconds: durationRef.current,
      hasUnsavedRecording: false,
      error: message
    });
  }

  function startTimer() {
    clearTimer();
    timerRef.current = window.setInterval(() => {
      durationRef.current += 1;
      setDurationSeconds(durationRef.current);
      onMetadataChange(currentMetadata("recording", true));
    }, 1000);
  }

  function clearTimer() {
    if (timerRef.current !== undefined) {
      window.clearInterval(timerRef.current);
      timerRef.current = undefined;
    }
  }

  function attachTrackEndedHandler(stream: MediaStream) {
    const track = stream.getAudioTracks()[0];
    if (!track) return;
    const handler = () => interruptRecording("Recording was interrupted. Please record again.");
    trackEndedHandlerRef.current = handler;
    track.addEventListener("ended", handler);
  }

  function stopStream() {
    const stream = streamRef.current;
    if (!stream) return;
    const track = stream.getAudioTracks()[0];
    if (track && trackEndedHandlerRef.current) track.removeEventListener("ended", trackEndedHandlerRef.current);
    stream.getTracks().forEach((item) => item.stop());
    streamRef.current = null;
    trackEndedHandlerRef.current = null;
  }

  function startVisualization(stream: MediaStream) {
    if (typeof window.AudioContext === "undefined") {
      setAmplitudes(Array.from({ length: 24 }, (_, index) => 12 + ((index * 17) % 42)));
      return;
    }
    const context = new window.AudioContext();
    const analyser = context.createAnalyser();
    analyser.fftSize = 64;
    context.createMediaStreamSource(stream).connect(analyser);
    const values = new Uint8Array(analyser.frequencyBinCount);
    audioContextRef.current = context;
    const draw = () => {
      analyser.getByteFrequencyData(values);
      setAmplitudes(Array.from({ length: 24 }, (_, index) => Math.max(8, Math.round((values[index] / 255) * 76))));
      animationRef.current = window.requestAnimationFrame(draw);
    };
    draw();
  }

  function stopVisualization() {
    if (animationRef.current !== undefined) window.cancelAnimationFrame(animationRef.current);
    animationRef.current = undefined;
    void audioContextRef.current?.close();
    audioContextRef.current = null;
    setAmplitudes(Array.from({ length: 24 }, () => 8));
  }

  function revokeAudioUrl() {
    if (!audioUrlRef.current) return;
    URL.revokeObjectURL?.(audioUrlRef.current);
    audioUrlRef.current = "";
    setAudioUrl("");
  }

  function currentMetadata(recordingStatus: RecordingMetadata["recordingStatus"], hasUnsavedRecording: boolean): RecordingMetadata {
    return {
      recordingStatus,
      durationSeconds: durationRef.current,
      mimeType: mimeTypeRef.current,
      createdAt: createdAtRef.current,
      hasUnsavedRecording
    };
  }

  const statusText = status === "recording"
    ? "Recording"
    : status === "paused"
      ? "Paused"
      : status === "stopped"
        ? "Recording ready"
        : status === "interrupted"
          ? "Interrupted"
          : "Ready to record";

  return (
    <div>
      <div className={`mb-4 flex items-center justify-center gap-2 text-lg font-bold ${status === "recording" ? "text-red-600" : "text-clinical"}`}>
        <span className={`h-3 w-3 rounded-full ${status === "recording" ? "animate-pulse bg-red-500" : "bg-clinical"}`} />
        {statusText}
      </div>
      <p className="text-5xl font-bold tracking-normal text-ink">{formatDuration(durationSeconds)}</p>
      <div className="mx-auto mt-8 flex h-28 max-w-sm items-center justify-center gap-1.5" aria-label="Microphone amplitude">
        {amplitudes.map((height, index) => (
          <span key={index} className={`w-1.5 rounded-full ${status === "recording" ? "bg-clinical" : "bg-[color:var(--color-accent-subtle)]"}`} style={{ height }} />
        ))}
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        {status === "idle" || status === "error" || status === "interrupted" ? (
          <button type="button" className="grid h-20 w-20 place-items-center rounded-full bg-[color:var(--color-accent)] text-white" aria-label="Start recording" onClick={startRecording}>
            <Mic size={32} aria-hidden="true" />
          </button>
        ) : null}
        {status === "recording" ? (
          <button type="button" className="grid h-20 w-20 place-items-center rounded-full bg-[color:var(--color-accent)] text-white" aria-label="Pause recording" onClick={pauseRecording}>
            <Pause size={32} fill="currentColor" aria-hidden="true" />
          </button>
        ) : null}
        {status === "paused" ? (
          <button type="button" className="grid h-20 w-20 place-items-center rounded-full bg-[color:var(--color-accent)] text-white" aria-label="Resume recording" onClick={resumeRecording}>
            <Play size={32} fill="currentColor" aria-hidden="true" />
          </button>
        ) : null}
        <button type="button" className="grid h-14 w-14 place-items-center rounded-full border border-line bg-[color:var(--color-surface-reading)] text-slate-600 disabled:opacity-35" aria-label="Stop recording" onClick={stopRecording} disabled={status !== "recording" && status !== "paused"}>
          <Square size={20} fill="currentColor" aria-hidden="true" />
        </button>
      </div>

      {audioUrl ? (
        <div className="mt-5 rounded-[var(--radius-panel)] border border-line bg-[color:var(--color-surface-reading)] p-4">
          <audio className="w-full" controls src={audioUrl} aria-label="Recorded audio playback" />
          <div className="mt-3 flex flex-wrap justify-center gap-2">
            <button type="button" className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-clinical px-4 py-2 text-sm font-semibold text-clinical" onClick={rerecord}>
              <RotateCcw size={17} aria-hidden="true" />
              Re-record
            </button>
            <button type="button" className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-red-200 px-4 py-2 text-sm font-semibold text-red-700" onClick={deleteRecording} aria-label="Delete recording">
              <Trash2 size={17} aria-hidden="true" />
              Delete
            </button>
          </div>
        </div>
      ) : null}

      {privacyNotice ? <p className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm font-semibold text-amber-900">Unsaved recording was cleared for privacy. Please record again.</p> : null}
      {error ? <p className="mt-4 rounded-xl border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-800" role="alert">{error}</p> : null}
      <p className="mt-3 text-sm font-semibold text-clinical">ASR/transcription is experimental and uses a local mock processing API after explicit upload.</p>
      <p className="mt-1 text-xs text-slate-600">Audio stays in memory only while this page is open. It is not uploaded automatically.</p>
    </div>
  );
}

function selectMimeType() {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  return candidates.find((type) => window.MediaRecorder.isTypeSupported?.(type)) ?? "";
}

function formatDuration(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return `00:${String(minutes).padStart(2, "0")}:${String(remainder).padStart(2, "0")}`;
}

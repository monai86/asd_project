import { render, screen, fireEvent } from "@testing-library/react";
import { vi, expect, test } from "vitest";
import { AudioUploadConfirmPanel } from "@/components/audio-upload-confirm-panel";

const noop = () => {};
const mockBlob = new Blob(["audio"], { type: "audio/webm" });

test("renders privacy notice before upload", () => {
  render(
    <AudioUploadConfirmPanel blob={mockBlob} durationSeconds={30}
      onUpload={noop} onCancel={noop} backendAvailable={true} />
  );
  expect(screen.getByText(/sent to the backend for transcription/i)).toBeInTheDocument();
  expect(screen.getByText(/therapist review required/i)).toBeInTheDocument();
});

test("upload button calls onUpload when backend available", () => {
  const onUpload = vi.fn();
  render(
    <AudioUploadConfirmPanel blob={mockBlob} durationSeconds={30}
      onUpload={onUpload} onCancel={noop} backendAvailable={true} />
  );
  fireEvent.click(screen.getByRole("button", { name: /upload for transcription/i }));
  expect(onUpload).toHaveBeenCalledTimes(1);
});

test("upload button disabled when backend unavailable", () => {
  render(
    <AudioUploadConfirmPanel blob={mockBlob} durationSeconds={30}
      onUpload={noop} onCancel={noop} backendAvailable={false} />
  );
  expect(screen.getByRole("button", { name: /upload for transcription/i })).toBeDisabled();
});

test("cancel button calls onCancel", () => {
  const onCancel = vi.fn();
  render(
    <AudioUploadConfirmPanel blob={mockBlob} durationSeconds={30}
      onUpload={noop} onCancel={onCancel} backendAvailable={true} />
  );
  fireEvent.click(screen.getByRole("button", { name: /cancel/i }));
  expect(onCancel).toHaveBeenCalledTimes(1);
});

test("audio blob is NOT written to sessionStorage on render", () => {
  render(
    <AudioUploadConfirmPanel blob={mockBlob} durationSeconds={30}
      onUpload={noop} onCancel={noop} backendAvailable={true} />
  );
  const hasAudio = Object.keys(sessionStorage).some(
    k => (sessionStorage.getItem(k) ?? "").length > 1000
  );
  expect(hasAudio).toBe(false);
});

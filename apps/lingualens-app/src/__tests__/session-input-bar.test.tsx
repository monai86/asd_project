import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { SessionInputBar } from "@/features/sessions/components/session-input-bar";

describe("SessionInputBar", () => {
  it("renders microphone record and send buttons", () => {
    render(<SessionInputBar onSendMessage={vi.fn()} onAudioRecord={vi.fn()} />);
    expect(screen.getByRole("button", { name: /start recording/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /send message/i })).toBeInTheDocument();
  });

  it("toggles recording state on mic button click", () => {
    const onAudioRecord = vi.fn();
    render(<SessionInputBar onSendMessage={vi.fn()} onAudioRecord={onAudioRecord} />);
    const micBtn = screen.getByRole("button", { name: /start recording/i });
    fireEvent.click(micBtn);
    expect(onAudioRecord).toHaveBeenCalledWith(true);
  });

  it("calls onSendMessage when text is entered and send clicked", () => {
    const onSendMessage = vi.fn();
    render(<SessionInputBar onSendMessage={onSendMessage} onAudioRecord={vi.fn()} />);
    const input = screen.getByPlaceholderText(/พิมพ์บันทึก/i);
    fireEvent.change(input, { target: { value: "ทดสอบ" } });
    fireEvent.click(screen.getByRole("button", { name: /send message/i }));
    expect(onSendMessage).toHaveBeenCalledWith("ทดสอบ");
  });

  it("disables send button when text is empty", () => {
    render(<SessionInputBar onSendMessage={vi.fn()} onAudioRecord={vi.fn()} />);
    expect(screen.getByRole("button", { name: /send message/i })).toBeDisabled();
  });
});

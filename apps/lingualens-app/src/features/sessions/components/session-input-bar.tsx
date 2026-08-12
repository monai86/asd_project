"use client";

import { useState, useRef } from "react";
import { Mic, MicOff, Paperclip, Send, Loader2 } from "lucide-react";

export function SessionInputBar({
  onSendMessage,
  onAudioRecord,
  onFileUpload,
  isProcessing = false,
}: {
  onSendMessage: (text: string) => void;
  onAudioRecord: (isRecording: boolean) => void;
  onFileUpload?: (file: File) => void;
  isProcessing?: boolean;
}) {
  const [text, setText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const toggleRecording = () => {
    const nextState = !isRecording;
    setIsRecording(nextState);
    onAudioRecord(nextState);
  };

  const handleSend = () => {
    if (!text.trim() || isProcessing) return;
    onSendMessage(text);
    setText("");
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && onFileUpload) {
      onFileUpload(file);
    }
    e.target.value = "";
  };

  return (
    <div className="border-t border-[#2f2f2f] bg-[#171717] p-3 md:p-4">
      <div className="mx-auto max-w-3xl">
        <div className="relative flex items-center gap-1 rounded-xl border border-[#2f2f2f] bg-[#212121] px-2 py-1.5 shadow-lg focus-within:border-[#10a37f]/60 transition-colors">
          {/* Microphone Record Toggle */}
          <button
            type="button"
            aria-label={isRecording ? "Stop recording" : "Start recording"}
            onClick={toggleRecording}
            disabled={isProcessing}
            className={`shrink-0 rounded-lg p-2 transition ${
              isRecording
                ? "bg-red-500/20 text-red-400 animate-pulse"
                : "text-slate-400 hover:bg-[#2f2f2f] hover:text-slate-200"
            } disabled:opacity-40`}
          >
            {isRecording ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
          </button>

          {/* File Upload */}
          <button
            type="button"
            aria-label="Upload audio file"
            onClick={() => fileInputRef.current?.click()}
            disabled={isProcessing}
            className="shrink-0 rounded-lg p-2 text-slate-400 hover:bg-[#2f2f2f] hover:text-slate-200 transition disabled:opacity-40"
          >
            <Paperclip className="h-4.5 w-4.5" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="audio/*,.mp3,.wav,.m4a"
            onChange={handleFileChange}
            className="hidden"
          />

          {/* Text Input */}
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            placeholder={
              isRecording
                ? "กำลังบันทึกเสียง..."
                : "พิมพ์บันทึกสังเกตพฤติกรรม หรือ คำสั่งวิเคราะห์..."
            }
            disabled={isProcessing}
            className="min-w-0 flex-1 bg-transparent px-2 py-1.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none disabled:opacity-40"
          />

          {/* Send / Processing Button */}
          <button
            type="button"
            aria-label="Send message"
            onClick={handleSend}
            disabled={!text.trim() || isProcessing}
            className="shrink-0 rounded-lg bg-[#10a37f] p-2 text-white transition hover:bg-[#1a7f64] disabled:opacity-30 disabled:cursor-not-allowed"
          >
            {isProcessing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </button>
        </div>

        {/* Recording indicator text */}
        {isRecording && (
          <div className="mt-2 flex items-center justify-center gap-2 text-xs text-red-400 animate-pulse">
            <span className="inline-block h-2 w-2 rounded-full bg-red-500" />
            กำลังบันทึกเสียง… แตะปุ่มไมค์อีกครั้งเพื่อหยุด
          </div>
        )}
      </div>
    </div>
  );
}

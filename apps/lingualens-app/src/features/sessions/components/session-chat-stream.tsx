"use client";

import { Bot, User, AudioLines, FileText, AlertTriangle } from "lucide-react";

export type ChatMessage = {
  id: string;
  role: "therapist" | "system" | "ai";
  type: "text" | "audio" | "transcript" | "finding" | "error";
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
};

function formatTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isAi = msg.role === "ai" || msg.role === "system";
  const isError = msg.type === "error";

  return (
    <div className={`flex gap-3 ${isAi ? "" : "flex-row-reverse"}`}>
      {/* Avatar */}
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
          isError
            ? "bg-red-500/20 text-red-400"
            : isAi
              ? "bg-[#10a37f]/20 text-[#10a37f]"
              : "bg-slate-600/30 text-slate-300"
        }`}
      >
        {isError ? (
          <AlertTriangle className="h-4 w-4" />
        ) : isAi ? (
          <Bot className="h-4 w-4" />
        ) : (
          <User className="h-4 w-4" />
        )}
      </div>

      {/* Bubble */}
      <div className={`max-w-[80%] space-y-1 ${isAi ? "" : "items-end text-right"}`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isError
              ? "border border-red-500/30 bg-red-500/10 text-red-300"
              : isAi
                ? "bg-[#2f2f2f] text-slate-100"
                : "bg-[#10a37f] text-white"
          }`}
        >
          {msg.type === "audio" && (
            <div className="mb-2 flex items-center gap-2 text-xs text-slate-400">
              <AudioLines className="h-3.5 w-3.5" />
              <span>ไฟล์เสียง</span>
            </div>
          )}
          {msg.type === "transcript" && (
            <div className="mb-2 flex items-center gap-2 text-xs text-slate-400">
              <FileText className="h-3.5 w-3.5" />
              <span>Transcript</span>
            </div>
          )}
          <p className="whitespace-pre-wrap">{msg.content}</p>
        </div>
        <span className="block text-[10px] text-slate-500">{formatTime(msg.timestamp)}</span>
      </div>
    </div>
  );
}

export function SessionChatStream({
  messages,
  isLoading = false,
}: {
  messages: ChatMessage[];
  isLoading?: boolean;
}) {
  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-4 py-6 md:px-8">
      <div className="mx-auto w-full max-w-3xl space-y-6">
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center py-20 text-center text-slate-500">
            <Bot className="mb-4 h-12 w-12 text-[#10a37f]/40" />
            <h3 className="text-lg font-medium text-slate-300">LinguaLens Clinical Assistant</h3>
            <p className="mt-2 max-w-sm text-sm leading-relaxed">
              เริ่มต้นบันทึกเสียง หรือพิมพ์บันทึกสังเกตพฤติกรรมเด็ก เพื่อเริ่มการวิเคราะห์ทางคลินิก
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}

        {/* AI Typing Indicator */}
        {isLoading && (
          <div className="flex gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#10a37f]/20 text-[#10a37f]">
              <Bot className="h-4 w-4" />
            </div>
            <div className="rounded-2xl bg-[#2f2f2f] px-4 py-3">
              <div className="flex items-center gap-1.5">
                <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:0ms]" />
                <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:150ms]" />
                <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

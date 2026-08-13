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
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full shadow-xs ${
          isError
            ? "bg-red-100 text-red-600"
            : isAi
              ? "bg-[#10a37f]/10 text-[#10a37f] border border-[#10a37f]/20"
              : "bg-slate-800 text-white"
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
      <div className={`max-w-[85%] space-y-1 ${isAi ? "" : "items-end text-right"}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-xs ${
            isError
              ? "border border-red-200 bg-red-50 text-red-900"
              : isAi
                ? "border border-slate-200/80 bg-slate-100/90 text-slate-900"
                : "bg-[#10a37f] text-white font-medium"
          }`}
        >
          {msg.type === "audio" && (
            <div className={`mb-1.5 flex items-center gap-1.5 text-xs font-semibold ${isAi ? "text-slate-500" : "text-emerald-100"}`}>
              <AudioLines className="h-3.5 w-3.5" />
              <span>ไฟล์เสียง</span>
            </div>
          )}
          {msg.type === "transcript" && (
            <div className={`mb-1.5 flex items-center gap-1.5 text-xs font-semibold ${isAi ? "text-slate-500" : "text-emerald-100"}`}>
              <FileText className="h-3.5 w-3.5" />
              <span>Transcript</span>
            </div>
          )}
          <p className="whitespace-pre-wrap">{msg.content}</p>
        </div>
        <span className="block text-[10px] font-medium text-slate-400 px-1">{formatTime(msg.timestamp)}</span>
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
    <div className="flex flex-1 flex-col overflow-y-auto px-4 py-6 md:px-8 bg-white">
      <div className="mx-auto w-full max-w-3xl space-y-6">
        {messages.length === 0 && !isLoading && (
          <div className="flex flex-col items-center justify-center py-20 text-center text-slate-500">
            <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#10a37f]/10 text-[#10a37f]">
              <Bot className="h-8 w-8" />
            </div>
            <h3 className="text-xl font-bold text-slate-800">LinguaLens Clinical Assistant</h3>
            <p className="mt-2 max-w-sm text-sm leading-relaxed text-slate-600">
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
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[#10a37f]/10 text-[#10a37f] border border-[#10a37f]/20">
              <Bot className="h-4 w-4" />
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-100 px-4 py-3">
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

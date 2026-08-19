"use client";

import React, { useState } from "react";
import { Check, Copy, FileCode } from "lucide-react";

export interface TalkbankUtterance {
  id?: string;
  speaker?: string;
  text: string;
  startMs?: number;
  endMs?: number;
  unclear?: boolean;
  flags?: string[];
}

export interface TalkbankChatViewerProps {
  rawCha?: string;
  utterances?: TalkbankUtterance[];
  sessionId?: string;
  childId?: string;
  className?: string;
}

export function TalkbankChatViewer({
  rawCha,
  utterances = [],
  sessionId = "SESS-001",
  childId = "CHI001",
  className = "",
}: TalkbankChatViewerProps) {
  const [copied, setCopied] = useState(false);

  // Generate standard TalkBank CHAT representation if rawCha is not directly supplied
  const chatContent = React.useMemo(() => {
    if (rawCha && rawCha.trim().length > 0) {
      return rawCha;
    }
    const lines = [
      "@UTF8",
      "@Begin",
      "@Languages:\ttha, eng",
      `@Participants:\tCHI ${childId} Child, INV Clinician`,
      `@ID:\ttha|LinguaLens|CHI|4;00.|male|ASD||Child||`,
      `@Media:\t${sessionId}, audio`,
      "",
    ];

    utterances.forEach((u) => {
      const spk = u.speaker || "CHI";
      let line = `*${spk}:\t${u.text}`;
      if (u.startMs !== undefined && u.endMs !== undefined && u.startMs !== null && u.endMs !== null) {
        line += ` \x15${u.startMs}_${u.endMs}\x15`;
      }
      lines.push(line);
      if (u.flags && u.flags.length > 0) {
        lines.push(`%xqa:\t[${u.flags.join(", ")}]`);
      }
    });

    lines.push("", "@End");
    return lines.join("\n");
  }, [rawCha, utterances, sessionId, childId]);

  const handleCopy = () => {
    navigator.clipboard.writeText(chatContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={`flex flex-col rounded-xl border border-slate-200 bg-white shadow-sm ${className}`}>
      {/* Header Toolbar */}
      <div className="flex items-center justify-between border-b border-slate-200 bg-slate-50/80 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <FileCode className="h-4 w-4 text-sky-600" />
          <span className="text-xs font-bold text-slate-800">
            TalkBank / CHAT Standard Syntax View
          </span>
          <span className="rounded bg-sky-100 px-1.5 py-0.5 text-[10px] font-semibold text-sky-700">
            @UTF8
          </span>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-xs hover:bg-slate-50 active:scale-98 transition-all"
        >
          {copied ? (
            <>
              <Check className="h-3.5 w-3.5 text-emerald-600" />
              <span className="text-emerald-700 font-semibold">Copied!</span>
            </>
          ) : (
            <>
              <Copy className="h-3.5 w-3.5 text-slate-500" />
              <span>Copy CHAT</span>
            </>
          )}
        </button>
      </div>

      {/* Syntax Render Panel */}
      <div className="max-h-[500px] overflow-auto p-4 font-mono text-xs leading-relaxed text-slate-800 selection:bg-sky-200">
        {chatContent.split("\n").map((line, idx) => {
          if (line.startsWith("@")) {
            return (
              <div key={idx} className="text-purple-700 font-semibold py-0.5">
                {line}
              </div>
            );
          }
          if (line.startsWith("*CHI:")) {
            const parts = line.split("\t");
            const spk = parts[0];
            const rest = parts.slice(1).join("\t");
            return (
              <div key={idx} className="py-0.5 hover:bg-emerald-50/50 rounded px-1 -mx-1">
                <span className="font-bold text-emerald-700">{spk}</span>
                <span className="text-slate-400">	</span>
                <span className="text-slate-900 font-medium">{rest}</span>
              </div>
            );
          }
          if (line.startsWith("*INV") || line.startsWith("*MOT") || line.startsWith("*FAT") || line.startsWith("*EXP")) {
            const parts = line.split("\t");
            const spk = parts[0];
            const rest = parts.slice(1).join("\t");
            return (
              <div key={idx} className="py-0.5 hover:bg-sky-50/50 rounded px-1 -mx-1">
                <span className="font-bold text-sky-700">{spk}</span>
                <span className="text-slate-400">	</span>
                <span className="text-slate-700">{rest}</span>
              </div>
            );
          }
          if (line.startsWith("%")) {
            return (
              <div key={idx} className="text-slate-500 italic py-0.5 pl-4">
                {line}
              </div>
            );
          }
          return (
            <div key={idx} className="text-slate-600 py-0.5">
              {line}
            </div>
          );
        })}
      </div>
    </div>
  );
}

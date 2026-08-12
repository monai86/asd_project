"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { Activity, ChevronLeft } from "lucide-react";
import Link from "next/link";

import { SessionChatStream, type ChatMessage } from "@/features/sessions/components/session-chat-stream";
import { SessionInputBar } from "@/features/sessions/components/session-input-bar";
import { ClinicalEvidenceDrawer, type FindingsData } from "@/features/sessions/components/clinical-evidence-drawer";

type SessionChatWorkspaceProps = {
  sessionId?: string;
  caseLabel?: string;
  childAge?: string;
  status?: string;
};

function generateId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function SessionChatWorkspace({
  sessionId = "new",
  caseLabel = "New Assessment Session",
  childAge,
  status = "intake",
}: SessionChatWorkspaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: generateId(),
      role: "ai",
      type: "text",
      content:
        "สวัสดีครับ ยินดีต้อนรับสู่ LinguaLens Clinical Assistant\n\nเริ่มต้นการประเมินได้โดย:\n• 🎙️ กดปุ่มไมค์เพื่อบันทึกเสียงสนทนา\n• 📎 อัปโหลดไฟล์เสียง (.mp3, .wav, .m4a)\n• ⌨️ พิมพ์บันทึกสังเกตพฤติกรรม\n\nพร้อมเมื่อไหร่ เริ่มได้เลยครับ!",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [findings, setFindings] = useState<FindingsData>({
    talkBankScore: undefined,
    receptiveScore: undefined,
    expressiveScore: undefined,
  });
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSendMessage = useCallback((text: string) => {
    // Add therapist message
    const therapistMsg: ChatMessage = {
      id: generateId(),
      role: "therapist",
      type: "text",
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, therapistMsg]);

    // Simulate AI processing response
    setIsProcessing(true);
    setTimeout(() => {
      const aiResponse: ChatMessage = {
        id: generateId(),
        role: "ai",
        type: "text",
        content: `บันทึกสังเกตพฤติกรรมเรียบร้อยแล้วครับ\n\nข้อมูลที่บันทึก: "${text}"\n\nกรุณาอัปโหลดไฟล์เสียงหรือบันทึกเสียงสดเพิ่มเติม เพื่อเริ่มการวิเคราะห์ทางคลินิก หรือกดปุ่ม "Clinical Findings" เพื่อดูผลวิเคราะห์เบื้องต้น`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, aiResponse]);
      setIsProcessing(false);
    }, 1500);
  }, []);

  const handleAudioRecord = useCallback((isRecording: boolean) => {
    if (isRecording) {
      const msg: ChatMessage = {
        id: generateId(),
        role: "system",
        type: "audio",
        content: "🎙️ เริ่มบันทึกเสียง...",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, msg]);
    } else {
      const msg: ChatMessage = {
        id: generateId(),
        role: "system",
        type: "audio",
        content: "✅ หยุดบันทึกเสียงแล้ว กำลังส่งไปประมวลผล...",
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, msg]);

      // Simulate transcription response
      setIsProcessing(true);
      setTimeout(() => {
        const transcriptMsg: ChatMessage = {
          id: generateId(),
          role: "ai",
          type: "transcript",
          content:
            "ผลการถอดความเสียง (Transcript):\n\nCHI: ช้าง ตัว ใหญ่ อยู่ ไหน\nINV: ช้างตัวใหญ่อยู่ตรงนั้นครับ เห็นไหม\nCHI: เห็น … แล้ว ก็ มี ลิง ด้วย",
          timestamp: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, transcriptMsg]);

        // Update findings after transcript
        setFindings({
          talkBankScore: 0.82,
          werScore: 0.15,
          receptiveScore: 0.78,
          expressiveScore: 0.71,
          pragmaticsScore: 0.65,
          riskCue: "moderate_receptive_delay",
        });
        setIsProcessing(false);
      }, 2000);
    }
  }, []);

  const handleFileUpload = useCallback((file: File) => {
    const msg: ChatMessage = {
      id: generateId(),
      role: "therapist",
      type: "audio",
      content: `📎 อัปโหลดไฟล์เสียง: ${file.name} (${(file.size / 1024).toFixed(0)} KB)`,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, msg]);

    setIsProcessing(true);
    setTimeout(() => {
      const aiMsg: ChatMessage = {
        id: generateId(),
        role: "ai",
        type: "text",
        content: `ได้รับไฟล์เสียง "${file.name}" เรียบร้อยแล้ว\nกำลังส่งไปประมวลผลด้วย Whisper Speech-to-Text + Speaker Diarization...\n\n⏳ โปรดรอสักครู่`,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, aiMsg]);
      setIsProcessing(false);
    }, 1000);
  }, []);

  return (
    <div className="flex h-full min-h-0 overflow-hidden">
      {/* Main Chat Canvas */}
      <div className="flex flex-1 flex-col min-w-0">
        {/* Session Header Bar */}
        <header className="flex items-center justify-between border-b border-[#2f2f2f] bg-[#212121] px-4 py-2.5">
          <div className="flex items-center gap-3 min-w-0">
            <Link
              href="/cases"
              className="shrink-0 rounded-md p-1 text-slate-400 hover:bg-[#2f2f2f] hover:text-slate-200 transition lg:hidden"
            >
              <ChevronLeft className="h-5 w-5" />
            </Link>
            <div className="min-w-0">
              <h1 className="truncate text-sm font-semibold text-slate-100">{caseLabel}</h1>
              <p className="text-xs text-slate-500">
                {childAge && <span>{childAge} · </span>}
                <span className="capitalize">{status}</span>
                {sessionId !== "new" && <span> · {sessionId.slice(0, 8)}</span>}
              </p>
            </div>
          </div>

          {/* Evidence Drawer Toggle */}
          <button
            type="button"
            onClick={() => setDrawerOpen(!drawerOpen)}
            className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              drawerOpen
                ? "bg-[#10a37f]/20 text-[#10a37f]"
                : "border border-[#2f2f2f] text-slate-400 hover:bg-[#2f2f2f] hover:text-slate-200"
            }`}
          >
            <Activity className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Clinical Findings</span>
          </button>
        </header>

        {/* Chat Stream Area */}
        <div className="flex-1 overflow-y-auto">
          <SessionChatStream messages={messages} isLoading={isProcessing} />
          <div ref={messagesEndRef} />
        </div>

        {/* Bottom Input Bar */}
        <SessionInputBar
          onSendMessage={handleSendMessage}
          onAudioRecord={handleAudioRecord}
          onFileUpload={handleFileUpload}
          isProcessing={isProcessing}
        />
      </div>

      {/* Clinical Evidence Drawer */}
      <ClinicalEvidenceDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        findings={findings}
        onViewReport={() => {
          window.open(`/reports/preview?session=${sessionId}`, "_blank");
        }}
      />
    </div>
  );
}

import Link from "next/link";
import { MessageSquare, Clock, CheckCircle2, ArrowRight, User } from "lucide-react";

export default function DemoTranscript() {
  const meta = {
    child: "น้องเอ (Ava)",
    age: "5 ปี 2 เดือน",
    date: "5 ก.ค. 2569",
    language: "ไทย-อังกฤษ (Bilingual)",
    turns: "12 รอบการสนทนา",
    duration: "1:50 นาที",
  };

  const lines = [
    { speaker: "SLP", time: "00:05", text: "สวัสดีค่ะน้องเอ วันนี้เราจะเล่นอะไรกันดีคะ" },
    { speaker: "CHI", time: "00:12", text: "เล่น... เล่นตุ๊กตา" },
    { speaker: "SLP", time: "00:18", text: "อ๋อ ตุ๊กตาสวยจัง แล้วตุ๊กตาชื่ออะไรคะ" },
    { speaker: "CHI", time: "00:25", text: "ชื่อ มิกกี้" },
    { speaker: "SLP", time: "00:35", text: "มิกกี้เหรอ แล้วมิกกี้ชอบทำอะไรคะ" },
    { speaker: "CHI", time: "00:42", text: "มิกกี้... กินข้าว... แล้วก็นอน" },
    { speaker: "SLP", time: "00:52", text: "เก่งมากค่ะ แล้ววันนี้น้องเอมาโรงเรียนยังไงคะ" },
    { speaker: "CHI", time: "01:05", text: "แม่... แม่มาส่ง" },
    { speaker: "SLP", time: "01:15", text: "แม่มาส่งเหรอคะ แล้วเจอเพื่อนบ้างไหม" },
    { speaker: "CHI", time: "01:28", text: "เจอ... เจอเพื่อน" },
    { speaker: "SLP", time: "01:38", text: "เล่นอะไรกันคะ" },
    { speaker: "CHI", time: "01:45", text: "เล่น... เล่นทราย" },
  ];

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-[-0.03em] text-[color:var(--color-text-strong)]">
            ถอดความบทสนทนา (Transcript)
          </h1>
          <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
            ตรวจสอบความถูกต้องของบทสนทนาก่อนนำไปวิเคราะห์ฟีเจอร์ทางภาษา
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 border border-emerald-100">
            <CheckCircle2 size={12} />
            ผ่านการตรวจสอบโดยนักบำบัด
          </span>
        </div>
      </div>

      {/* Meta Card */}
      <div className="grid gap-4 rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <p className="text-xs text-[color:var(--color-text-subtle)] font-medium">ชื่อ/รหัสจำลอง</p>
          <p className="text-sm font-semibold text-[color:var(--color-text-strong)] mt-0.5">{meta.child}</p>
        </div>
        <div>
          <p className="text-xs text-[color:var(--color-text-subtle)] font-medium">อายุเมื่อประเมิน</p>
          <p className="text-sm font-semibold text-[color:var(--color-text-strong)] mt-0.5">{meta.age}</p>
        </div>
        <div>
          <p className="text-xs text-[color:var(--color-text-subtle)] font-medium">วันที่ประเมิน</p>
          <p className="text-sm font-semibold text-[color:var(--color-text-strong)] mt-0.5">{meta.date}</p>
        </div>
        <div>
          <p className="text-xs text-[color:var(--color-text-subtle)] font-medium">ภาษาที่ใช้ประเมิน</p>
          <p className="text-sm font-semibold text-[color:var(--color-text-strong)] mt-0.5">{meta.language}</p>
        </div>
      </div>

      {/* Chat Container */}
      <div className="overflow-hidden rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-white/50">
        {/* Chat Header */}
        <div className="border-b border-[color:var(--color-border)] bg-[color:var(--color-surface-muted)] px-5 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MessageSquare size={16} className="text-[color:var(--color-text-muted)]" />
            <span className="text-sm font-semibold text-[color:var(--color-text-strong)]">บทสนทนา (12 บทพูด)</span>
          </div>
          <div className="flex items-center gap-4 text-xs text-[color:var(--color-text-muted)]">
            <span className="flex items-center gap-1"><Clock size={12} /> ความยาว {meta.duration}</span>
            <span>ตอบสนอง 100%</span>
          </div>
        </div>

        {/* Message bubbles */}
        <div className="p-6 space-y-4 max-h-[500px] overflow-y-auto bg-slate-50/30">
          {lines.map((line, index) => {
            const isChi = line.speaker === "CHI";
            return (
              <div
                key={index}
                className={`flex gap-3 max-w-[80%] ${isChi ? "ml-auto flex-row-reverse" : "mr-auto"}`}
              >
                {/* Speaker Avatar/Badge */}
                <div className={`h-8 w-8 shrink-0 rounded-full flex items-center justify-center font-bold text-xs ${
                  isChi ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"
                }`}>
                  {line.speaker}
                </div>

                {/* Message Box */}
                <div>
                  <div className={`rounded-[var(--radius-panel)] p-4 ${
                    isChi
                      ? "bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)] rounded-tr-none"
                      : "bg-white text-[color:var(--color-text-strong)] border border-[color:var(--color-border)] rounded-tl-none"
                  }`}>
                    <p className="text-sm leading-relaxed">{line.text}</p>
                  </div>
                  <p className={`text-[10px] text-[color:var(--color-text-subtle)] mt-1 ${isChi ? "text-right" : "text-left"}`}>
                    Timestamp {line.time}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-between border-t border-[color:var(--color-border)] pt-6">
        <Link
          href="/demo/upload"
          className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-white px-5 text-sm font-semibold text-[color:var(--color-text-strong)] transition hover:bg-slate-50"
        >
          ย้อนกลับ
        </Link>
        <Link
          href="/demo/features"
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-pill)] bg-[color:var(--color-accent)] px-6 text-sm font-semibold text-white transition hover:bg-[color:var(--color-accent-strong)]"
        >
          ถัดไป: ดูผลวิเคราะห์
          <ArrowRight size={16} />
        </Link>
      </div>
    </div>
  );
}

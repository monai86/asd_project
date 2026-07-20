import Link from "next/link";
import { UploadCloud, CheckCircle2, FileAudio, ArrowRight } from "lucide-react";

export default function DemoUpload() {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-semibold tracking-[-0.03em] text-[color:var(--color-text-strong)]">
          อัปโหลดไฟล์เสียง (Upload Audio)
        </h1>
        <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
          อัปโหลดคลิปวิดีโอหรือเสียงจากเซสชันการบำบัดเพื่อถอดความและวิเคราะห์ทางภาษาพูด
        </p>
      </div>

      {/* Drag & Drop Zone */}
      <div className="relative flex flex-col items-center justify-center rounded-[var(--radius-panel)] border-2 border-dashed border-[color:var(--color-border)] bg-white p-12 text-center transition hover:border-[color:var(--color-accent)]">
        <div className="flex h-12 w-12 items-center justify-center text-[color:var(--color-accent)]">
          <UploadCloud size={32} />
        </div>
        <h3 className="mt-4 text-lg font-semibold text-[color:var(--color-text-strong)]">
          ลากไฟล์มาวางที่นี่ หรือ คลิกเพื่อเลือกไฟล์
        </h3>
        <p className="mt-2 text-sm text-[color:var(--color-text-muted)]">
          รองรับไฟล์วิดีโอและไฟล์เสียง เช่น .mp4, .wav, .m4a หรือไฟล์ถอดคำรหัส .cha
        </p>
        <span className="mt-4 inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
          ขนาดสูงสุด 100MB
        </span>
      </div>

      {/* Upload Progress (Static Showcase) */}
      <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-5">
        <div className="flex items-start gap-4">
          <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-600">
            <FileAudio size={20} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-3">
              <p className="truncate text-sm font-semibold text-[color:var(--color-text-strong)]">
                session_recording_ava_2026-07-05.wav
              </p>
              <span className="shrink-0 text-xs font-semibold text-emerald-600 flex items-center gap-1">
                <CheckCircle2 size={12} />
                อัปโหลดสำเร็จ
              </span>
            </div>
            <p className="mt-1 text-xs text-[color:var(--color-text-subtle)]">
              12.4 MB · ถอดความเสียงอัตโนมัติด้วย Whisper (Thai-English)
            </p>
            {/* Custom Progress Bar */}
            <div className="mt-3 h-1.5 w-full rounded-full bg-slate-100 overflow-hidden">
              <div className="h-full w-full rounded-full bg-emerald-500" />
            </div>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-between border-t border-[color:var(--color-border)] pt-6">
        <Link
          href="/demo/dashboard"
          className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-white px-5 text-sm font-semibold text-[color:var(--color-text-strong)] transition hover:bg-slate-50"
        >
          กลับหน้าหลัก
        </Link>
        <Link
          href="/demo/transcript"
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-pill)] bg-[color:var(--color-accent)] px-6 text-sm font-semibold text-white transition hover:bg-[color:var(--color-accent-strong)]"
        >
          ถัดไป: ดูบทสนทนา
          <ArrowRight size={16} />
        </Link>
      </div>
    </div>
  );
}

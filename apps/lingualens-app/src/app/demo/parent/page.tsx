import Link from "next/link";
import { Sparkles, FileText, CalendarDays, BookOpen, Palette, MessageSquare, ArrowLeft, Heart } from "lucide-react";

export default function DemoParent() {
  const tips = [
    { title: "อ่านหนังสือก่อนนอน", desc: "อ่านนิทานร่วมกับน้องเอ ชวนชี้นิ้วบอกสิ่งต่าง ๆ และถามความรู้สึกตัวละคร", icon: BookOpen, color: "text-blue-600 bg-blue-50" },
    { title: "กิจกรรมวาดรูปและบอกคำศัพท์", desc: "ชวนน้องเอระบายสีสิ่งของรอบตัว แล้วให้บอกชื่อสิ่งของพร้อมลักษณะเด่น", icon: Palette, color: "text-purple-600 bg-purple-50" },
    { title: "ถามคำถามปลายเปิด", desc: "เปลี่ยนการถาม 'ใช่/ไม่ใช่' เป็นคำถาม 'ทำไม' หรือ 'อย่างไร' ระหว่างกิจกรรมร่วมกัน", icon: MessageSquare, color: "text-amber-600 bg-amber-50" },
  ];

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      {/* Future Feature Banner */}
      <div className="rounded-[var(--radius-shell)] border border-amber-200 bg-amber-50 p-6 flex flex-col sm:flex-row items-center gap-4">
        <span className="grid h-12 w-12 place-items-center rounded-xl bg-orange-100 text-orange-600 shrink-0 animate-pulse">
          <Sparkles size={24} />
        </span>
        <div>
          <h4 className="font-bold text-orange-950 text-sm">💡 ฟีเจอร์จำลองสำหรับอนาคต (Parent Portal Mockup)</h4>
          <p className="mt-1 text-xs text-orange-900 leading-normal">
            หน้าจอนี้จัดทำขึ้นเพื่อนำเสนอไอเดียบริการเสริมสำหรับผู้ปกครอง เพื่อติดตามผลลัพธ์การฝึกพูดและการบำบัดของลูกหลานจากทางบ้าน (Coming Soon)
          </p>
        </div>
      </div>

      {/* Parent Portal Header */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-[-0.03em] text-[color:var(--color-text-strong)] flex items-center gap-2">
            <Heart className="text-rose-500 fill-rose-500" />
            สวัสดีค่ะ คุณแม่ของน้องเอ (Ava)
          </h1>
          <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
            ยินดีต้อนรับสู่แดชบอร์ดความร่วมมือเพื่อพัฒนาการสื่อสารของน้องเอ
          </p>
        </div>
      </div>

      {/* Progress Cards */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Simple Progress Cards */}
        <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-5 space-y-4 md:col-span-2">
          <h3 className="font-bold text-sm text-[color:var(--color-text-strong)]">สรุปภาพรวมความก้าวหน้า (Progress Summary)</h3>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-xs text-[color:var(--color-text-muted)] mb-1">
                <span>ความตั้งใจและการโต้ตอบ (Responsiveness)</span>
                <span className="font-bold text-emerald-600">95% (ดีมาก)</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                <div className="h-full bg-emerald-500 rounded-full" style={{ width: "95%" }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs text-[color:var(--color-text-muted)] mb-1">
                <span>การเชื่อมโยงคำศัพท์ (Vocabulary Connection)</span>
                <span className="font-bold text-blue-600">75% (ปกติ)</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                <div className="h-full bg-blue-500 rounded-full" style={{ width: "75%" }} />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs text-[color:var(--color-text-muted)] mb-1">
                <span>ความยาวรูปประโยคพูด (Sentence Length)</span>
                <span className="font-bold text-amber-600">60% (ควรส่งเสริมเพิ่ม)</span>
              </div>
              <div className="h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                <div className="h-full bg-amber-500 rounded-full" style={{ width: "60%" }} />
              </div>
            </div>
          </div>
        </div>

        {/* Dynamic Widget */}
        <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-5 space-y-4 flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-sm text-[color:var(--color-text-strong)]">นัดหมายการฝึกพูดครั้งถัดไป</h3>
            <div className="mt-4 flex gap-3.5">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-rose-50 text-rose-600">
                <CalendarDays size={20} />
              </span>
              <div>
                <p className="text-sm font-semibold text-[color:var(--color-text-strong)]">วันจันทร์ที่ 19 ก.ค. 2569</p>
                <p className="text-xs text-[color:var(--color-text-muted)] mt-0.5">เวลา 10:30 น. (บำบัดต่อเนื่อง)</p>
              </div>
            </div>
          </div>
          <button className="w-full inline-flex h-9 items-center justify-center rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-[color:var(--color-page-bg)] text-xs font-semibold hover:border-[color:var(--color-text-strong)] transition">
            ขอเลื่อนนัดหมาย
          </button>
        </div>
      </div>

      {/* Action Cards */}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-5 flex items-center justify-between transition cursor-pointer">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-blue-50 text-blue-600">
              <FileText size={20} />
            </span>
            <div>
              <h4 className="text-sm font-semibold text-[color:var(--color-text-strong)]">ดูรายงานการประเมินล่าสุด</h4>
              <p className="text-xs text-[color:var(--color-text-subtle)] mt-0.5">อัปเดตล่าสุด: วันที่ 5 ก.ค. 2569</p>
            </div>
          </div>
        </div>

        <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-5 flex items-center justify-between transition cursor-pointer">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-rose-50 text-rose-600">
              <CalendarDays size={20} />
            </span>
            <div>
              <h4 className="text-sm font-semibold text-[color:var(--color-text-strong)]">บันทึกวิดีโอกิจกรรมฝึกการพูด</h4>
              <p className="text-xs text-[color:var(--color-text-subtle)] mt-0.5">อัปโหลดคลิปที่น้องฝึกพูดที่บ้าน</p>
            </div>
          </div>
        </div>
      </div>

      {/* Home Activities Tips */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">กิจกรรมกระตุ้นการสื่อสารที่บ้านแนะนำ</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {tips.map((tip) => {
            const Icon = tip.icon;
            return (
              <div
                key={tip.title}
                className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-5 flex flex-col justify-between"
              >
                <div className="space-y-3">
                  <span className={`grid h-8 w-8 place-items-center rounded-lg ${tip.color}`}>
                    <Icon size={18} />
                  </span>
                  <h4 className="text-sm font-bold text-[color:var(--color-text-strong)]">{tip.title}</h4>
                  <p className="text-xs text-[color:var(--color-text-muted)] leading-relaxed">{tip.desc}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Action Buttons Bottom */}
      <div className="flex items-center justify-between border-t border-[color:var(--color-border)] pt-6">
        <Link
          href="/demo/report"
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-white px-5 text-sm font-semibold text-[color:var(--color-text-strong)] transition hover:bg-slate-50"
        >
          <ArrowLeft size={16} />
          ย้อนกลับ
        </Link>
        <Link
          href="/demo/dashboard"
          className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-pill)] bg-[color:var(--color-accent)] px-6 text-sm font-semibold text-white transition hover:bg-[color:var(--color-accent-strong)]"
        >
          กลับสู่แดชบอร์ดหลัก
        </Link>
      </div>
    </div>
  );
}

import Link from "next/link";
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Sparkles,
} from "lucide-react";

export default function DemoFeatures() {
  const features = [
    {
      title: "จำนวนรอบสนทนา",
      english: "Turn Count",
      value: "12 รอบ",
      description: "จำนวนการตอบกลับระหว่างเด็กและนักบำบัด",
      status: "บันทึกได้",
      tone: "success",
      caution: "ข้อมูลตัวอย่างจากเซสชันนี้ ใช้เพื่อทบทวนรูปแบบการผลัดกันสนทนาเท่านั้น",
    },
    {
      title: "จำนวนคำทั้งหมด",
      english: "Total Words (CHI)",
      value: "28 คำ",
      description: "คำศัพท์ทั้งหมดที่เด็กใช้สื่อสารในเซสชัน",
      status: "ข้อมูลเชิงพรรณนา",
      tone: "warning",
      caution: "จำนวนคำที่สังเกตได้ในตัวอย่างนี้ ควรพิจารณาร่วมกับบริบทของกิจกรรมและการทบทวนโดยนักบำบัด",
    },
    {
      title: "ความยาวเฉลี่ยประโยค",
      english: "Mean Length of Utterance (MLU)",
      value: "2.3 คำ/ประโยค",
      description: "ค่าเฉลี่ยความยาวคำพูดต่อหนึ่งรอบประโยค",
      status: "ข้อมูลเชิงพรรณนา",
      tone: "warning",
      caution: "ค่านี้สรุปความยาวคำพูดในตัวอย่าง ไม่ได้ใช้เปรียบเทียบตามช่วงวัยหรือเป็นข้อสรุปเชิงวินิจฉัย",
    },
    {
      title: "ความหลากหลายคำศัพท์",
      english: "Type-Token Ratio (TTR)",
      value: "0.71",
      description: "สัดส่วนคำศัพท์ไม่ซ้ำต่อคำศัพท์ทั้งหมด",
      status: "ข้อมูลเชิงพรรณนา",
      tone: "success",
      caution: "ค่านี้อธิบายสัดส่วนคำไม่ซ้ำในตัวอย่าง และไม่ควรตีความแยกจากขนาดหรือบริบทของตัวอย่าง",
    },
    {
      title: "คลังคำศัพท์ไม่ซ้ำ",
      english: "Vocabulary Size",
      value: "20 คำ",
      description: "จำนวนคำศัพท์ที่แตกต่างกันทั้งหมดในบทสนทนา",
      status: "ข้อมูลเชิงพรรณนา",
      tone: "warning",
      caution: "จำนวนคำไม่ซ้ำที่สังเกตได้ในตัวอย่างนี้ ใช้ประกอบการวางแผนกิจกรรมโดยนักบำบัด",
    },
    {
      title: "อัตราการตอบสนอง",
      english: "Response Rate",
      value: "100%",
      description: "อัตราการตอบกลับเมื่อนักบำบัดตั้งคำถาม",
      status: "ตอบครบในตัวอย่าง",
      tone: "success",
      caution: "พบการตอบกลับทุกคำถามในตัวอย่างนี้ โดยไม่สรุปพฤติกรรมนอกบริบทของเซสชัน",
    },
  ];

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-semibold tracking-[-0.03em] text-[color:var(--color-text-strong)] flex items-center gap-2">
          <Sparkles className="text-[color:var(--color-accent)]" />
          ผลวิเคราะห์ฟีเจอร์ทางภาษา (Linguistic Features)
        </h1>
        <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
          สถิติและค่าที่คำนวณจากบทสนทนาตัวอย่างของ น้องเอ (Ava) เพื่อการทบทวนโดยนักบำบัด
        </p>
      </div>

      {/* Feature Cards Grid */}
      <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        {features.map((feat) => (
          <div
            key={feat.title}
            className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-5 flex flex-col justify-between"
          >
            <div>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-bold text-[color:var(--color-text-strong)]">{feat.title}</h3>
                  <p className="text-xs text-[color:var(--color-text-subtle)] font-mono">{feat.english}</p>
                </div>
                <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                  feat.tone === "success"
                    ? "bg-[color:var(--color-success-bg)] text-[color:var(--color-success-text)]"
                    : "bg-[color:var(--color-warning-bg)] text-[color:var(--color-warning-text)]"
                }`}>
                  {feat.status}
                </span>
              </div>
              <p className="mt-4 text-3xl font-extrabold text-[color:var(--color-text-strong)]">{feat.value}</p>
              <p className="mt-2 text-xs text-[color:var(--color-text-muted)] leading-relaxed">{feat.description}</p>
            </div>
            <div className="mt-4 pt-3 border-t border-[color:var(--color-border)]">
              <p className="text-xs font-semibold text-[color:var(--color-text-subtle)] uppercase tracking-wider">Safety & CAUTION</p>
              <p className="mt-1 text-xs text-[color:var(--color-text-muted)] leading-normal">{feat.caution}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Strengths & Observations Summary */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Strengths */}
        <div className="rounded-[var(--radius-panel)] border-l-4 border-emerald-500 bg-[color:var(--color-surface-strong)] p-6 space-y-3">
          <h3 className="text-lg font-bold text-emerald-800 flex items-center gap-2">
            <CheckCircle2 size={20} />
            รูปแบบที่สังเกตได้ (Observed Patterns)
          </h3>
          <ul className="space-y-2 text-sm text-[color:var(--color-text-muted)] list-disc pl-5 leading-relaxed">
            <li><strong>การตอบสนองในตัวอย่าง (Response Rate 100%):</strong> ตอบกลับทุกครั้งที่นักบำบัดมีปฏิสัมพันธ์ด้วยในบทสนทนาตัวอย่างนี้</li>
            <li><strong>คำไม่ซ้ำในตัวอย่าง (TTR 0.71):</strong> พบคำไม่ซ้ำ 20 คำจากคำพูดทั้งหมด 28 คำ ควรอ่านค่านี้ร่วมกับขนาดของตัวอย่าง</li>
            <li><strong>การเข้าร่วมกิจกรรม (Engagement):</strong> เข้าร่วมกิจกรรมเล่นตามบทบาทกับตุ๊กตามิกกี้ตลอดช่วงตัวอย่างที่บันทึกไว้</li>
          </ul>
        </div>

        {/* Observations */}
        <div className="rounded-[var(--radius-panel)] border-l-4 border-amber-500 bg-[color:var(--color-surface-strong)] p-6 space-y-3">
          <h3 className="text-lg font-bold text-amber-800 flex items-center gap-2">
            <AlertCircle size={20} />
            ข้อสังเกตและโอกาสพัฒนา (Observations)
          </h3>
          <ul className="space-y-2 text-sm text-[color:var(--color-text-muted)] list-disc pl-5 leading-relaxed">
            <li><strong>รูปแบบความยาวประโยค (MLU 2.3):</strong> ประโยคส่วนใหญ่ในตัวอย่างเป็นคำโดดหรือประโยคสั้น 2 คำ เช่น &quot;เล่นตุ๊กตา&quot;, &quot;ชื่อมิกกี้&quot; ข้อมูลนี้ใช้เพื่อช่วยนักบำบัดทบทวนตัวอย่างเท่านั้น</li>
            <li><strong>คำที่สังเกตได้:</strong> ตัวอย่างนี้มีคำกริยาและคำคุณศัพท์จำนวนหนึ่ง นักบำบัดสามารถใช้รายการคำที่บันทึกไว้ประกอบการเลือกกิจกรรมครั้งถัดไป</li>
          </ul>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-between border-t border-[color:var(--color-border)] pt-6">
        <Link
          href="/demo/transcript"
          className="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-white px-5 text-sm font-semibold text-[color:var(--color-text-strong)] transition hover:bg-slate-50"
        >
          ย้อนกลับ
        </Link>
        <Link
          href="/demo/report"
          className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-pill)] bg-[color:var(--color-accent)] px-6 text-sm font-semibold text-white transition hover:bg-[color:var(--color-accent-strong)]"
        >
          ถัดไป: ดูรายงานสรุป
          <ArrowRight size={16} />
        </Link>
      </div>
    </div>
  );
}

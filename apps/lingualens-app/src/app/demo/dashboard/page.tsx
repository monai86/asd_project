import Link from "next/link";
import {
  CalendarDays,
  Upload,
  FileText,
  BarChart3,
  Clock,
  CheckCircle2,
  Loader2,
  Users,
  TrendingUp,
} from "lucide-react";

export default function DemoDashboard() {
  const stats = [
    { label: "เคสทั้งหมด", value: "8", helper: "เคสเด็กในการดูแล", icon: Users, color: "text-blue-600 bg-blue-50" },
    { label: "เซสชันวันนี้", value: "3", helper: "นัดหมายบำบัดวันนี้", icon: CalendarDays, color: "text-purple-600 bg-purple-50" },
    { label: "รอตรวจสอบภาษา", value: "2", helper: "บทสนทนารอการตรวจทาน", icon: FileText, color: "text-amber-600 bg-amber-50" },
    { label: "รายงานพร้อมส่ง", value: "1", helper: "สรุปผลบำบัดสมบูรณ์", icon: CheckCircle2, color: "text-emerald-600 bg-emerald-50" },
  ];

  const appointments = [
    { time: "10:30 น.", child: "น้องเอ (Ava)", age: "5 ปี 2 เดือน", type: "Language sample review", status: "พร้อมอัปโหลดเสียง" },
    { time: "13:00 น.", child: "น้องอีธาน (Ethan)", age: "4 ปี 8 เดือน", type: "Articulation therapy", status: "เสร็จสิ้นเซสชัน" },
    { time: "15:30 น.", child: "น้องเจคอบ (Jacob)", age: "6 ปี 1 เดือน", type: "Fluency follow-up", status: "รอเข้าพบ" },
  ];

  const recentActivity = [
    { child: "น้องเอ", desc: "สกัดฟีเจอร์ภาษาและจำลองรายงานฉบับร่างแล้ว", time: "10 นาทีที่แล้ว", type: "report" },
    { child: "น้องอีธาน", desc: "บันทึกบทสนทนาและแก้ไข Speaker Labels เสร็จสิ้น", time: "1 ชั่วโมงที่แล้ว", type: "transcript" },
    { child: "น้องเจคอบ", desc: "อัปโหลดไฟล์เสียงการบำบัดเรียบร้อยแล้ว", time: "2 ชั่วโมงที่แล้ว", type: "upload" },
  ];

  return (
    <div className="space-y-8">
      {/* Welcome Header */}
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-[-0.03em] text-[color:var(--color-text-strong)]">
            สวัสดี, Dr. Somchai
          </h1>
          <p className="mt-1 text-sm text-[color:var(--color-text-muted)]">
            Therapist Workspace — ระบบช่วยวิเคราะห์ภาษาพูดและสนับสนุนการตัดสินใจทางคลินิก
          </p>
        </div>
        <div>
          <Link
            href="/demo/upload"
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-[var(--radius-pill)] bg-[color:var(--color-accent)] px-5 text-sm font-semibold text-white transition hover:bg-[color:var(--color-accent-strong)]"
          >
            <Upload size={16} />
            เริ่มอัปโหลดเสียงบำบัด
          </Link>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.label}
              className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-5"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-[color:var(--color-text-muted)]">{stat.label}</span>
                <span className={`grid h-8 w-8 place-items-center rounded-lg ${stat.color}`}>
                  <Icon size={18} />
                </span>
              </div>
              <p className="mt-2 text-3xl font-bold text-[color:var(--color-text-strong)]">{stat.value}</p>
              <p className="mt-1 text-xs text-[color:var(--color-text-subtle)]">{stat.helper}</p>
            </div>
          );
        })}
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Today's Agenda */}
        <div className="space-y-4 lg:col-span-2">
          <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">ตารางการบำบัดวันนี้ (Today&apos;s Agenda)</h2>
          <div className="space-y-3">
            {appointments.map((appt) => (
              <div
                key={appt.child}
                className="flex flex-col gap-4 rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex items-start gap-3.5">
                  <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)] font-semibold text-sm">
                    {appt.time.split(" ")[0]}
                  </div>
                  <div>
                    <h3 className="font-semibold text-[color:var(--color-text-strong)]">{appt.child}</h3>
                    <p className="text-xs text-[color:var(--color-text-muted)]">
                      อายุ {appt.age} · {appt.type}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                    appt.status === "พร้อมอัปโหลดเสียง"
                      ? "bg-blue-50 text-blue-700 border border-blue-100"
                      : appt.status === "เสร็จสิ้นเซสชัน"
                      ? "bg-emerald-50 text-emerald-700 border border-emerald-100"
                      : "bg-slate-100 text-slate-700 border border-slate-200"
                  }`}>
                    {appt.status}
                  </span>
                  {appt.status === "พร้อมอัปโหลดเสียง" && (
                    <Link
                      href="/demo/upload"
                      className="inline-flex h-9 items-center justify-center rounded-[var(--radius-pill)] border border-[color:var(--color-border)] bg-[color:var(--color-page-bg)] px-3 text-xs font-semibold hover:border-[color:var(--color-text-strong)]"
                    >
                      จัดการ
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Activity */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-[color:var(--color-text-strong)]">กิจกรรมล่าสุด (Recent Activity)</h2>
          <div className="rounded-[var(--radius-panel)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-strong)] p-5 space-y-4">
            {recentActivity.map((act, index) => (
              <div key={index} className="flex gap-3">
                <div className="mt-0.5 shrink-0">
                  {act.type === "report" && (
                    <span className="flex h-6.5 w-6.5 items-center justify-center rounded-full bg-emerald-50 text-emerald-600">
                      <CheckCircle2 size={14} />
                    </span>
                  )}
                  {act.type === "transcript" && (
                    <span className="flex h-6.5 w-6.5 items-center justify-center rounded-full bg-blue-50 text-blue-600">
                      <FileText size={14} />
                    </span>
                  )}
                  {act.type === "upload" && (
                    <span className="flex h-6.5 w-6.5 items-center justify-center rounded-full bg-amber-50 text-amber-600">
                      <Loader2 size={14} className="animate-spin" />
                    </span>
                  )}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-[color:var(--color-text-strong)]">
                    <span className="font-semibold">{act.child}</span> — {act.desc}
                  </p>
                  <p className="mt-1 text-xs text-[color:var(--color-text-subtle)] flex items-center gap-1">
                    <Clock size={10} />
                    {act.time}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

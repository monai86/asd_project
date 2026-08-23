"use client";

import { Printer, ShieldCheck, FileDown, Building2 } from "lucide-react";

export interface ClinicalReportData {
  /* Demographics */
  childName: string;
  childCode?: string;
  age: string;
  gender?: string;
  evaluator: string;
  date: string;
  location?: string;

  /* Assessment Sections */
  receptiveSummary: string;
  expressiveSummary: string;
  pragmaticsSummary?: string;
  behavioralObservations?: string;

  /* Metrics (optional ML-derived scores) */
  talkBankScore?: number;
  receptiveScore?: number;
  expressiveScore?: number;

  /* Recommendations */
  recommendations?: string[];

  /* Sign-off & Audit */
  signedAt?: string;
  hash?: string;
  reportVersion?: string;
  /** Therapist + date of the server-recorded reviewed-cues acknowledgement. */
  cuesAcknowledgedBy?: string;
  cuesAcknowledgedAt?: string;
}

function ScoreDisplay({ label, score }: { label: string; score?: number }) {
  if (score == null) return null;
  const pct = (score * 100).toFixed(0);
  return (
    <div className="flex items-center justify-between border-b border-slate-200 py-1.5 last:border-0">
      <span className="text-slate-600">{label}</span>
      <span className="font-semibold text-slate-900">{pct}%</span>
    </div>
  );
}

export function ClinicalPdfReport({ data }: { data: ClinicalReportData }) {
  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="min-h-screen bg-[#171717] print:bg-white print:min-h-0">
      {/* Toolbar (hidden when printing) */}
      <div className="sticky top-0 z-10 border-b border-[#2f2f2f] bg-[#212121]/95 backdrop-blur print:hidden">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3 md:px-8">
          <h1 className="text-lg font-bold text-slate-100">Clinical Assessment Report</h1>
          <div className="flex items-center gap-2">
            <button
              onClick={handlePrint}
              className="flex items-center gap-2 rounded-lg bg-[#10a37f] px-4 py-2 text-sm font-medium text-white shadow-lg hover:bg-[#1a7f64] transition"
            >
              <Printer className="h-4 w-4" />
              Print / Download PDF
            </button>
          </div>
        </div>
      </div>

      {/* A4 Document */}
      <div className="mx-auto max-w-4xl px-4 py-8 md:px-8 print:max-w-none print:px-0 print:py-0">
        <div className="bg-white text-slate-900 shadow-2xl rounded-sm print:shadow-none print:rounded-none">

          {/* ===== PAGE CONTENT ===== */}
          <div className="p-8 md:p-12 print:p-[15mm] space-y-8 print:space-y-6 [print-color-adjust:exact] [-webkit-print-color-adjust:exact]">

            {/* ── Document Header ── */}
            <header className="border-b-2 border-slate-900 pb-5">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 text-[#10a37f] print:text-emerald-700 mb-1">
                    <Building2 className="h-5 w-5" />
                    <span className="text-xs font-bold uppercase tracking-widest">LinguaLens Clinical Suite</span>
                  </div>
                  <h2 className="text-2xl font-bold uppercase tracking-tight text-slate-900 print:text-xl">
                    Speech-Language Assessment Report
                  </h2>
                  <p className="mt-0.5 text-sm font-medium text-slate-500">
                    แบบรายงานผลการประเมินพัฒนาการทางภาษาและการสื่อสาร
                  </p>
                </div>
                <div className="text-right text-xs text-slate-500 shrink-0">
                  <div>Date: {data.date}</div>
                  {data.reportVersion && <div>Version: {data.reportVersion}</div>}
                </div>
              </div>
            </header>

            {/* ── Patient Demographics ── */}
            <section>
              <h3 className="mb-3 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-200 pb-1">
                ข้อมูลทั่วไป (Patient Demographics)
              </h3>
              <div className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
                <div><span className="font-semibold text-slate-700">ชื่อเด็ก:</span> <span className="text-slate-900">{data.childName}</span></div>
                <div><span className="font-semibold text-slate-700">อายุ:</span> <span className="text-slate-900">{data.age}</span></div>
                {data.childCode && (
                  <div><span className="font-semibold text-slate-700">รหัสเด็ก:</span> <span className="text-slate-900">{data.childCode}</span></div>
                )}
                {data.gender && (
                  <div><span className="font-semibold text-slate-700">เพศ:</span> <span className="text-slate-900">{data.gender}</span></div>
                )}
                <div><span className="font-semibold text-slate-700">ผู้ประเมิน:</span> <span className="text-slate-900">{data.evaluator}</span></div>
                <div><span className="font-semibold text-slate-700">วันที่ประเมิน:</span> <span className="text-slate-900">{data.date}</span></div>
                {data.location && (
                  <div className="col-span-2"><span className="font-semibold text-slate-700">สถานที่:</span> <span className="text-slate-900">{data.location}</span></div>
                )}
              </div>
            </section>

            {/* ── Metric Scores (if available) ── */}
            {(data.talkBankScore != null || data.receptiveScore != null || data.expressiveScore != null) && (
              <section>
                <h3 className="mb-3 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-200 pb-1">
                  คะแนนสรุป (Summary Scores)
                </h3>
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
                  <ScoreDisplay label="TalkBank Feature Score" score={data.talkBankScore} />
                  <ScoreDisplay label="Receptive Language" score={data.receptiveScore} />
                  <ScoreDisplay label="Expressive Language" score={data.expressiveScore} />
                </div>
                <p className="mt-1 text-[10px] text-slate-400 italic">
                  Research prototype scores — non-diagnostic. Therapist clinical judgment required.
                </p>
              </section>
            )}

            {/* ── Assessment Findings ── */}
            <section className="space-y-5 print:break-inside-avoid">
              <h3 className="mb-3 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-200 pb-1">
                ผลการประเมิน (Assessment Findings)
              </h3>

              <div>
                <h4 className="font-bold text-sm text-slate-800 mb-1">1. การเข้าใจภาษา (Receptive Language)</h4>
                <p className="text-sm text-slate-700 leading-relaxed pl-4">{data.receptiveSummary}</p>
              </div>

              <div>
                <h4 className="font-bold text-sm text-slate-800 mb-1">2. การแสดงออกทางภาษา (Expressive Language)</h4>
                <p className="text-sm text-slate-700 leading-relaxed pl-4">{data.expressiveSummary}</p>
              </div>

              {data.pragmaticsSummary && (
                <div>
                  <h4 className="font-bold text-sm text-slate-800 mb-1">3. การสื่อสารตามบริบทสังคม (Pragmatics)</h4>
                  <p className="text-sm text-slate-700 leading-relaxed pl-4">{data.pragmaticsSummary}</p>
                </div>
              )}

              {data.behavioralObservations && (
                <div>
                  <h4 className="font-bold text-sm text-slate-800 mb-1">4. พฤติกรรมและการตอบสนอง (Behavioral Observations)</h4>
                  <p className="text-sm text-slate-700 leading-relaxed pl-4">{data.behavioralObservations}</p>
                </div>
              )}
            </section>

            {/* ── Recommendations ── */}
            {data.recommendations && data.recommendations.length > 0 && (
              <section className="print:break-inside-avoid">
                <h3 className="mb-3 text-xs font-bold uppercase tracking-widest text-slate-400 border-b border-slate-200 pb-1">
                  ข้อเสนอแนะ (Clinical Recommendations)
                </h3>
                <ul className="list-disc pl-8 text-sm text-slate-700 space-y-1.5 leading-relaxed">
                  {data.recommendations.map((rec, i) => (
                    <li key={i}>{rec}</li>
                  ))}
                </ul>
              </section>
            )}

            {/* ── Sign-Off & Audit ── */}
            <footer className="mt-12 pt-6 border-t-2 border-slate-900 print:break-inside-avoid">
              <div className="flex items-end justify-between">
                {/* Hash verification */}
                {data.hash && (
                  <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono">
                    <ShieldCheck className="h-4 w-4 text-emerald-600 print:text-emerald-800" />
                    <div>
                      <div>SHA-256 Verified Snapshot</div>
                      <div className="mt-0.5">{data.hash.slice(0, 32)}...</div>
                      {data.signedAt && <div>Signed: {data.signedAt}</div>}
                      {data.cuesAcknowledgedAt && (
                        <div className="mt-0.5">
                          Reviewed cues acknowledged: {data.cuesAcknowledgedBy ?? "Therapist"} — {new Date(data.cuesAcknowledgedAt).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Signature block */}
                <div className="text-center text-sm">
                  <div className="mb-1 h-[1px] w-52 bg-slate-400" />
                  <div className="font-semibold text-slate-800">{data.evaluator}</div>
                  <div className="text-xs text-slate-500">นักอรรถบำบัด / Speech-Language Pathologist</div>
                  <div className="text-[10px] text-slate-400 mt-0.5">{data.date}</div>
                </div>
              </div>
            </footer>
          </div>
        </div>
      </div>

      {/* Print CSS */}
      <style jsx global>{`
        @media print {
          @page {
            size: A4 portrait;
            margin: 0;
          }
          body {
            -webkit-print-color-adjust: exact;
            print-color-adjust: exact;
          }
          .print\\:hidden { display: none !important; }
        }
      `}</style>
    </div>
  );
}

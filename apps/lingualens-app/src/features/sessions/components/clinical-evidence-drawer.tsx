"use client";

import { X, Activity, AlertCircle, BarChart3, FileCheck, ChevronRight } from "lucide-react";

export type FindingsData = {
  talkBankScore?: number;
  riskCue?: string;
  receptiveScore?: number;
  expressiveScore?: number;
  pragmaticsScore?: number;
  werScore?: number;
  stale?: boolean;
};

function ScoreCard({
  label,
  value,
  suffix = "%",
  color = "emerald",
}: {
  label: string;
  value?: number;
  suffix?: string;
  color?: "emerald" | "amber" | "red" | "blue";
}) {
  const colorMap = {
    emerald: "text-emerald-400",
    amber: "text-amber-400",
    red: "text-red-400",
    blue: "text-blue-400",
  };
  return (
    <div className="rounded-xl border border-[#2f2f2f] bg-[#171717] p-3">
      <div className="text-[11px] font-medium uppercase tracking-wider text-slate-500">{label}</div>
      <div className={`mt-1 text-2xl font-bold ${colorMap[color]}`}>
        {value != null ? `${(value * 100).toFixed(0)}${suffix}` : "—"}
      </div>
    </div>
  );
}

export function ClinicalEvidenceDrawer({
  isOpen,
  onClose,
  findings,
  onViewReport,
}: {
  isOpen: boolean;
  onClose: () => void;
  findings?: FindingsData;
  onViewReport?: () => void;
}) {
  return (
    <>
      {/* Mobile / Tablet backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm xl:hidden"
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <aside
        className={`fixed inset-y-0 right-0 z-50 flex w-full max-w-sm flex-col bg-[#212121] border-l border-[#2f2f2f] shadow-2xl transition-transform duration-300 xl:static xl:z-auto xl:max-w-[360px] xl:translate-x-0 ${
          isOpen ? "translate-x-0" : "translate-x-full xl:hidden"
        }`}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[#2f2f2f] px-4 py-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-200">
            <Activity className="h-4 w-4 text-[#10a37f]" />
            Clinical Findings
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 hover:bg-[#2f2f2f] transition"
            aria-label="Close evidence drawer"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Stale Warning */}
        {findings?.stale && (
          <div className="mx-4 mt-3 flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span>Findings are stale — Transcript has been updated. Regenerate analysis.</span>
          </div>
        )}

        {/* Score Cards */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <ScoreCard
              label="TalkBank Score"
              value={findings?.talkBankScore}
              color="emerald"
            />
            <ScoreCard
              label="WER (Word Error)"
              value={findings?.werScore}
              suffix="%"
              color={findings?.werScore && findings.werScore > 0.3 ? "red" : "blue"}
            />
            <ScoreCard
              label="Receptive Lang."
              value={findings?.receptiveScore}
              color="emerald"
            />
            <ScoreCard
              label="Expressive Lang."
              value={findings?.expressiveScore}
              color="amber"
            />
          </div>

          {/* Risk Cue Alert */}
          {findings?.riskCue && (
            <div className="rounded-xl border border-amber-500/20 bg-amber-500/10 p-3">
              <div className="flex items-center gap-2 text-sm font-medium text-amber-200">
                <AlertCircle className="h-4 w-4" />
                Clinical Observation Cue
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-amber-300/80">
                {findings.riskCue.replace(/_/g, " ")}
                <br />
                <span className="mt-1 block text-[10px] text-amber-400/60 italic">
                  Non-diagnostic research indicator only. Therapist review required.
                </span>
              </p>
            </div>
          )}

          {/* Pragmatics Section */}
          {findings?.pragmaticsScore != null && (
            <div className="rounded-xl border border-[#2f2f2f] bg-[#171717] p-3">
              <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
                <BarChart3 className="h-3.5 w-3.5" />
                Pragmatics / Social Interaction
              </div>
              <div className="mt-2 h-2 w-full rounded-full bg-[#2f2f2f]">
                <div
                  className="h-2 rounded-full bg-[#10a37f] transition-all duration-500"
                  style={{ width: `${(findings.pragmaticsScore * 100).toFixed(0)}%` }}
                />
              </div>
              <div className="mt-1 text-right text-xs text-slate-500">
                {(findings.pragmaticsScore * 100).toFixed(0)}%
              </div>
            </div>
          )}
        </div>

        {/* View Report Button */}
        {onViewReport && (
          <div className="border-t border-[#2f2f2f] p-4">
            <button
              type="button"
              onClick={onViewReport}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#10a37f] px-4 py-2.5 text-sm font-medium text-white shadow hover:bg-[#1a7f64] transition"
            >
              <FileCheck className="h-4 w-4" />
              View Clinical Report
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        )}
      </aside>
    </>
  );
}

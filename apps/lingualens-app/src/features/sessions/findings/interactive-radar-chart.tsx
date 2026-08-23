"use client";

import React, { useState } from "react";
import { Activity, AlertTriangle, CheckCircle2, Info, TrendingUp } from "lucide-react";

export interface RadarAxis {
  key: string;
  label: string;
  labelTh: string;
  value: number | null;
  norm: number;
  unit: string;
}

export interface InteractiveRadarChartProps {
  axes?: RadarAxis[];
  childName?: string;
  sessionDate?: string;
}

export function InteractiveRadarChart({
  axes: customAxes,
  childName = "Child",
  sessionDate,
}: InteractiveRadarChartProps) {
  const [hoveredAxis, setHoveredAxis] = useState<RadarAxis | null>(null);

  const defaultAxes: RadarAxis[] = [
    { key: "mlu_words", label: "MLU-w", labelTh: "ความยาวประโยค", value: 3.2, norm: 3.5, unit: "คำ" },
    { key: "ttr", label: "TTR Lexical", labelTh: "ความหลากหลายคำ", value: 0.78, norm: 0.75, unit: "" },
    { key: "turn_taking", label: "Turn-Taking", labelTh: "การผลัดกันพูด", value: 0.95, norm: 0.90, unit: "" },
    { key: "intelligibility", label: "Intelligibility", labelTh: "ความชัดเจน", value: 0.94, norm: 0.95, unit: "%" },
    { key: "speech_rate", label: "Speech Rate", labelTh: "ความเร็วการพูด", value: 88, norm: 90, unit: "wpm" },
    { key: "f0_iqr", label: "Prosody IQR", labelTh: "ช่วงระดับเสียง", value: 34.5, norm: 35.0, unit: "Hz" },
  ];

  const axes = customAxes || defaultAxes;
  const n = axes.length;

  const size = 380;
  const center = size / 2;
  const radius = 135;

  // Calculate polygon points
  const rings = [0.25, 0.5, 0.75, 1.0, 1.25];

  const getCoordinates = (index: number, ratio: number) => {
    const angle = -Math.PI / 2 + (2 * Math.PI * index) / n;
    const r = radius * (ratio / 1.25);
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
    };
  };

  // Typical Development Baseline (100% = 1.0 ratio)
  const normPoints = axes
    .map((_, i) => {
      const { x, y } = getCoordinates(i, 1.0);
      return `${x},${y}`;
    })
    .join(" ");

  // Child values polygon
  const childPoints = axes
    .map((ax, i) => {
      let ratio = 0.05;
      if (ax.value !== null && ax.norm > 0) {
        ratio = Math.max(0.15, Math.min(1.3, ax.value / ax.norm));
      }
      const { x, y } = getCoordinates(i, ratio);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="rounded-xl border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] p-5 shadow-xs">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[color:var(--color-border)] pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[color:var(--color-accent-soft)] text-[color:var(--color-accent-strong)]">
            <Activity className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-[color:var(--color-text-strong)]">
              Radar Comparison vs TD Normative Bands
            </h3>
            <p className="text-xs text-[color:var(--color-text-muted)]">
              เปรียบเทียบ 6 มิติทางภาษากับเกณฑ์พัฒนาการเด็กสมวัย (Typical Development Baseline)
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <span className="flex items-center gap-1.5 font-medium text-emerald-700">
            <span className="inline-block h-2 w-4 rounded-full border border-emerald-600 border-dashed bg-emerald-100"></span>
            เกณฑ์ปกติสมวัย (TD Norm 100%)
          </span>
          <span className="flex items-center gap-1.5 font-medium text-[color:var(--color-accent-strong)]">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-[color:var(--color-accent)]"></span>
            ผลของเด็กในเซสชันนี้
          </span>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 items-center gap-6 lg:grid-cols-12">
        {/* SVG Canvas */}
        <div className="relative flex justify-center lg:col-span-7">
          <svg width={size} height={size} className="overflow-visible">
            {/* Grid Rings */}
            {rings.map((ringRatio, rIdx) => {
              const pts = axes
                .map((_, i) => {
                  const { x, y } = getCoordinates(i, ringRatio);
                  return `${x},${y}`;
                })
                .join(" ");
              const isNorm = ringRatio === 1.0;
              return (
                <polygon
                  key={rIdx}
                  points={pts}
                  fill="none"
                  stroke={isNorm ? "#10b981" : "#e2e8f0"}
                  strokeWidth={isNorm ? 1.5 : 1}
                  strokeDasharray={isNorm ? "4 3" : undefined}
                />
              );
            })}

            {/* Radial Spokes */}
            {axes.map((ax, i) => {
              const { x, y } = getCoordinates(i, 1.25);
              return (
                <line
                  key={i}
                  x1={center}
                  y1={center}
                  x2={x}
                  y2={y}
                  stroke="#e2e8f0"
                  strokeWidth={1}
                />
              );
            })}

            {/* Norm Baseline Polygon */}
            <polygon
              points={normPoints}
              fill="rgba(16, 185, 129, 0.05)"
              stroke="#10b981"
              strokeWidth={1.75}
              strokeDasharray="4 3"
            />

            {/* Child Polygon */}
            <polygon
              points={childPoints}
              fill="rgba(2, 132, 199, 0.18)"
              stroke="#0284c7"
              strokeWidth={2.5}
            />

            {/* Child Node Points */}
            {axes.map((ax, i) => {
              let ratio = 0.05;
              if (ax.value !== null && ax.norm > 0) {
                ratio = Math.max(0.15, Math.min(1.3, ax.value / ax.norm));
              }
              const { x, y } = getCoordinates(i, ratio);
              const isHovered = hoveredAxis?.key === ax.key;

              return (
                <g key={i}>
                  <circle
                    cx={x}
                    cy={y}
                    r={isHovered ? 6 : 4}
                    fill={ax.value !== null ? "#0284c7" : "#94a3b8"}
                    stroke="#ffffff"
                    strokeWidth={1.5}
                    className="cursor-pointer transition-all duration-150"
                    onMouseEnter={() => setHoveredAxis(ax)}
                    onMouseLeave={() => setHoveredAxis(null)}
                  />
                </g>
              );
            })}

            {/* Axis Labels */}
            {axes.map((ax, i) => {
              const { x, y } = getCoordinates(i, 1.48);
              const isHovered = hoveredAxis?.key === ax.key;
              return (
                <text
                  key={i}
                  x={x}
                  y={y}
                  textAnchor="middle"
                  dominantBaseline="central"
                  className={`text-xs font-semibold transition-colors duration-150 ${
                    isHovered ? "fill-sky-700 font-bold" : "fill-slate-700"
                  }`}
                >
                  <tspan x={x} dy="-0.6em">{ax.label}</tspan>
                  <tspan x={x} dy="1.2em" className="fill-slate-500 font-normal">
                    {ax.labelTh}
                  </tspan>
                </text>
              );
            })}
          </svg>
        </div>

        {/* Breakdown & Benchmark Cards */}
        <div className="space-y-3 lg:col-span-5">
          <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600">
            <div className="flex items-center gap-1.5 font-semibold text-slate-800">
              <Info className="h-3.5 w-3.5 text-sky-600" />
              สรุปผลเปรียบเทียบเทียบเกณฑ์สมวัย:
            </div>
            <p className="mt-1 text-xs text-slate-500">
              ค่าเปอร์เซ็นต์คำนวณจากสัดส่วนเทียบกับเกณฑ์สมวัย (TD Reference Benchmark)
            </p>
          </div>

          <div className="divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white">
            {axes.map((ax) => {
              const pct =
                ax.value !== null && ax.norm > 0
                  ? Math.round((ax.value / ax.norm) * 100)
                  : null;
              const isSelected = hoveredAxis?.key === ax.key;

              let statusColor = "text-emerald-700 bg-emerald-50 border-emerald-200";
              let statusText = "สมวัย";
              if (pct === null) {
                statusColor = "text-slate-600 bg-slate-50 border-slate-200";
                statusText = "ไม่มีเสียง";
              } else if (pct < 65) {
                statusColor = "text-amber-800 bg-amber-50 border-amber-200";
                statusText = "ควรส่งเสริม";
              } else if (pct < 85) {
                statusColor = "text-sky-800 bg-sky-50 border-sky-200";
                statusText = "กำลังพัฒนา";
              }

              return (
                <div
                  key={ax.key}
                  className={`flex items-center justify-between p-2.5 transition-colors ${
                    isSelected ? "bg-sky-50/70" : "hover:bg-slate-50/50"
                  }`}
                  onMouseEnter={() => setHoveredAxis(ax)}
                  onMouseLeave={() => setHoveredAxis(null)}
                >
                  <div>
                    <span className="font-semibold text-slate-800">{ax.label}</span>{" "}
                    <span className="text-xs text-slate-500">({ax.labelTh})</span>
                    <div className="text-xs text-slate-500">
                      วัดได้:{" "}
                      <strong className="text-slate-700">
                        {ax.value !== null ? `${ax.value} ${ax.unit}` : "N/A"}
                      </strong>{" "}
                      | เกณฑ์: {ax.norm} {ax.unit}
                    </div>
                  </div>

                  <div className="text-right">
                    <span
                      className={`inline-block rounded border px-2 py-0.5 text-xs font-semibold ${statusColor}`}
                    >
                      {pct !== null ? `${pct}% · ${statusText}` : statusText}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

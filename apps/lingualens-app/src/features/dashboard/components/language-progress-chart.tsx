"use client";

import { useMemo, useState } from "react";

import type {
  DashboardTrendCase,
  DashboardTrendFeature,
  DashboardTrendPoint,
} from "@/lib/workflow";

const CHART_WIDTH = 640;
const CHART_HEIGHT = 176;
const PAD_X = 12;
const PAD_TOP = 16;
const PAD_BOTTOM = 14;

type Trends = {
  features: DashboardTrendFeature[];
  cases: DashboardTrendCase[];
};

function formatDate(value: string): string {
  const date = new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatValue(value: number): string {
  if (Number.isInteger(value)) return String(value);
  return String(parseFloat(value.toFixed(2)));
}

function pointsForFeature(
  trendCase: DashboardTrendCase | undefined,
  featureKey: string,
): Array<DashboardTrendPoint & { value: number }> {
  if (!trendCase) return [];
  return trendCase.points
    .map((point) => ({
      ...point,
      value: typeof point.values[featureKey] === "number" ? (point.values[featureKey] as number) : Number.NaN,
    }))
    .filter((point) => Number.isFinite(point.value));
}

function ChartGeometry({ points }: { points: Array<{ value: number }> }) {
  const values = points.map((point) => point.value);
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const range = rawMax - rawMin || 1;
  const min = rawMin - range * 0.18;
  const max = rawMax + range * 0.18;
  const innerWidth = CHART_WIDTH - PAD_X * 2;
  const innerHeight = CHART_HEIGHT - PAD_TOP - PAD_BOTTOM;

  const x = (index: number) =>
    points.length === 1
      ? CHART_WIDTH / 2
      : PAD_X + (index * innerWidth) / (points.length - 1);
  const y = (value: number) =>
    PAD_TOP + innerHeight - ((value - min) / (max - min)) * innerHeight;

  const linePath = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${x(index).toFixed(1)},${y(point.value).toFixed(1)}`)
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${CHART_WIDTH} ${CHART_HEIGHT}`}
      role="img"
      aria-label={`Line chart of ${points.length} value${points.length === 1 ? "" : "s"} across sessions`}
      className="h-auto w-full text-[color:var(--color-accent-strong)]"
      preserveAspectRatio="xMidYMid meet"
    >
      <line
        x1={PAD_X}
        y1={CHART_HEIGHT - PAD_BOTTOM}
        x2={CHART_WIDTH - PAD_X}
        y2={CHART_HEIGHT - PAD_BOTTOM}
        stroke="currentColor"
        strokeOpacity={0.15}
        strokeWidth={1}
      />
      {points.length > 1 ? (
        <path
          d={linePath}
          fill="none"
          stroke="currentColor"
          strokeWidth={2.5}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ) : null}
      {points.map((point, index) => (
        <circle
          key={index}
          cx={x(index)}
          cy={y(point.value)}
          r={5}
          fill="currentColor"
        />
      ))}
    </svg>
  );
}

export function LanguageProgressChart({ trends }: { trends: Trends }) {
  const [featureKey, setFeatureKey] = useState(trends.features[0]?.key ?? "");
  const [caseId, setCaseId] = useState(
    [...trends.cases].sort((a, b) => b.points.length - a.points.length)[0]?.case_id ?? "",
  );

  const feature = trends.features.find((item) => item.key === featureKey) ?? trends.features[0];
  const selectedCase = trends.cases.find((item) => item.case_id === caseId) ?? trends.cases[0];
  const points = useMemo(
    () => pointsForFeature(selectedCase, feature?.key ?? ""),
    [selectedCase, feature],
  );

  if (!feature || trends.cases.length === 0) {
    return (
      <p className="mt-4 rounded-[var(--radius-card)] border border-dashed border-[color:var(--color-border)] p-5 text-sm leading-6 text-[color:var(--color-text-muted)]">
        No language-progress data yet. Extract features from a session to start
        tracking MLU, NDW, and TTR across sessions.
      </p>
    );
  }

  const singleCase = trends.cases.length === 1 ? selectedCase : undefined;

  return (
    <div className="mt-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="grid min-w-0 gap-1 text-sm font-medium text-[color:var(--color-text-muted)]">
          Feature
          <select
            className="min-h-11 w-full min-w-0 max-w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-3 text-sm text-[color:var(--color-text-strong)] outline-none transition focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] sm:w-56"
            value={feature.key}
            onChange={(event) => setFeatureKey(event.target.value)}
          >
            {trends.features.map((item) => (
              <option key={item.key} value={item.key}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        {trends.cases.length > 1 ? (
          <label className="grid min-w-0 gap-1 text-sm font-medium text-[color:var(--color-text-muted)]">
            Case
            <select
              className="min-h-11 w-full min-w-0 max-w-full rounded-[var(--radius-card)] border border-[color:var(--color-border)] bg-[color:var(--color-surface-reading)] px-3 text-sm text-[color:var(--color-text-strong)] outline-none transition focus-visible:ring-4 focus-visible:ring-[color:var(--color-focus-ring)] sm:w-56"
              value={selectedCase.case_id}
              onChange={(event) => setCaseId(event.target.value)}
            >
              {trends.cases.map((item) => (
                <option key={item.case_id} value={item.case_id}>
                  {item.case_label}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <p className="text-sm font-medium text-[color:var(--color-text-muted)]">
            Case: <span className="text-[color:var(--color-text-strong)]">{singleCase?.case_label}</span>
          </p>
        )}
      </div>

      {points.length === 0 ? (
        <p className="mt-5 rounded-[var(--radius-card)] border border-dashed border-[color:var(--color-border)] p-5 text-sm leading-6 text-[color:var(--color-text-muted)]">
          No {feature.label.toLowerCase()} data for {selectedCase.case_label} yet.
          Extract features from a language-sample session to see it here.
        </p>
      ) : (
        <>
          {points.length === 1 ? (
            <p className="mt-4 text-sm leading-6 text-[color:var(--color-text-muted)]">
              One session with {feature.label.toLowerCase()} data so far — add
              more sessions to see the trend line.
            </p>
          ) : null}
          <div className="mt-4">
            <ChartGeometry points={points} />
            <p className="mt-1 text-xs text-[color:var(--color-text-subtle)]">
              Unit: {feature.unit} · across {points.length} session{points.length === 1 ? "" : "s"}
            </p>
          </div>
          <table className="mt-4 w-full max-w-sm border-collapse text-sm">
            <caption className="sr-only">
              {feature.label} values by session for {selectedCase.case_label}
            </caption>
            <thead>
              <tr className="border-b border-[color:var(--color-border)] text-left">
                <th scope="col" className="py-2 pr-4 font-medium text-[color:var(--color-text-muted)]">
                  Session date
                </th>
                <th scope="col" className="py-2 font-medium text-[color:var(--color-text-muted)]">
                  {feature.label}
                </th>
              </tr>
            </thead>
            <tbody>
              {points.map((point) => (
                <tr key={point.session_id} className="border-b border-[color:var(--color-border)] last:border-b-0">
                  <td className="py-2 pr-4 text-[color:var(--color-text-muted)]">{formatDate(point.session_date)}</td>
                  <td className="py-2 font-semibold text-[color:var(--color-text-strong)]">{formatValue(point.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}

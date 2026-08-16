/**
 * Benchmark baseline gate for CI.
 *
 * Compares `benchmarks/results/transcript-benchmark-latest.json` (written by
 * `npm run bench:transcript`) against the committed reference baseline
 * `benchmarks/results/transcript-benchmark-reference.json`.
 *
 * Rationale: interaction latency is hardware/runner sensitive, so the gate is
 * relative — a CI run must stay within `latencyToleranceFactor` of the
 * reference machine (2x absorbs shared-runner noise) and above absolute
 * scroll-fps floors. A real regression (e.g. the 79/137 ms keystroke regressions
 * documented in benchmarks/README.md) exceeds even the tolerant band.
 *
 * Recalibration: after a few green CI runs, refresh the reference file from the
 * actual runner by editing `reference.*` values (keep the tolerance factor).
 */
import { readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const projectRoot = process.cwd();
const resultPath = path.resolve(projectRoot, "benchmarks/results/transcript-benchmark-latest.json");
const referencePath = path.resolve(projectRoot, "benchmarks/results/transcript-benchmark-reference.json");

const [rawResults, rawReference] = await Promise.all([readFile(resultPath, "utf8"), readFile(referencePath, "utf8")]);
const results = JSON.parse(rawResults);
const reference = JSON.parse(rawReference);

const { latencyToleranceFactor, minimumScrollFps } = reference.comparison;
const failures = [];
const checks = [];

const lineEntries = new Map(results.results.map((entry) => [entry.lineCount, entry]));
const byLine = (lineCount) => {
  const entry = lineEntries.get(lineCount);
  if (!entry) throw new Error(`Benchmark results are missing the ${lineCount}-line measurement.`);
  return entry.summary;
};

const latencyChecks = [
  ["line100", 100, "keystrokeMs", "keystrokeP95Ms"],
  ["line100", 100, "selectionMs", "selectionP95Ms"],
  ["line100", 100, "filterMs", "filterP95Ms"],
  ["line500", 500, "keystrokeMs", "keystrokeP95Ms"],
  ["line500", 500, "selectionMs", "selectionP95Ms"],
  ["line500", 500, "filterMs", "filterP95Ms"],
  ["line1000", 1000, "keystrokeMs", "keystrokeP95Ms"],
  ["line1000", 1000, "selectionMs", "selectionP95Ms"],
  ["line1000", 1000, "filterMs", "filterP95Ms"],
];

for (const [referenceKey, lineCount, metric, referenceMetric] of latencyChecks) {
  const referenceValue = reference.reference[referenceKey][referenceMetric];
  const limit = referenceValue * latencyToleranceFactor;
  const actual = byLine(lineCount)[metric].p95;
  const label = `${lineCount}-line ${metric.replace("Ms", "")} p95`;
  checks.push({ label, actual, limit, direction: "at-or-below" });
  if (actual > limit) {
    failures.push(`${label} ${actual} ms exceeds the baseline limit of ${limit} ms (reference ${referenceValue} ms x ${latencyToleranceFactor}).`);
  }
}

const fpsChecks = [
  ["line500", 500, "minimumScrollFps.line500"],
  ["line1000", 1000, "minimumScrollFps.line1000"],
];

for (const [referenceKey, lineCount, limitPath] of fpsChecks) {
  const limit = minimumScrollFps[referenceKey];
  const entry = lineEntries.get(lineCount);
  const actual = Math.min(...entry.runs.map((run) => run.scrollFps));
  const label = `${lineCount}-line scroll fps (worst sampled run)`;
  checks.push({ label, actual, limit, direction: "at-or-above" });
  if (actual < limit) {
    failures.push(`${label} ${actual.toFixed(1)} fps is below the floor of ${limit} fps.`);
  }
}

const lines = [`Benchmark baseline gate — ${results.capturedAt}`, `Conditions: ${results.conditions.platform} / ${results.conditions.cpu}`, ""];
for (const check of checks) {
  const passed = check.direction === "at-or-above" ? check.actual >= check.limit : check.actual <= check.limit;
  lines.push(`${passed ? "PASS" : "FAIL"}  ${check.label.padEnd(46)} actual ${String(check.actual).padStart(9)}  limit ${String(check.limit).padStart(9)}`);
}
lines.push("");

if (failures.length > 0) {
  lines.push(`${failures.length} benchmark baseline violation(s):`);
  for (const failure of failures) lines.push(`  - ${failure}`);
  process.stderr.write(`${lines.join("\n")}\n`);
  process.exit(1);
}

process.stdout.write(`${lines.join("\n")}\nBenchmark within baseline tolerance. ✓\n`);

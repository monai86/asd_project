import { gzipSync } from "node:zlib";
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import process from "node:process";

const projectRoot = process.cwd();
const logPath = path.resolve(projectRoot, process.argv[2] ?? ".local/next-build.log");
const budgetPath = path.join(projectRoot, "bundle-budgets.json");
const chunkRoot = path.join(projectRoot, ".next/static/chunks");
const ansiPattern = /\u001b\[[0-9;]*m/g;

const [rawLog, rawBudgets] = await Promise.all([
  readFile(logPath, "utf8"),
  readFile(budgetPath, "utf8"),
]);
const log = rawLog.replace(ansiPattern, "");
const budgets = JSON.parse(rawBudgets);
const routeMeasurements = new Map();

for (const line of log.split(/\r?\n/)) {
  const routeMatch = line.match(/^[┌├└]\s+[○ƒ]\s+(\/\S*)\s+[\d.]+\s+(?:B|kB)\s+([\d.]+)\s+kB\s*$/);
  if (routeMatch) routeMeasurements.set(routeMatch[1], Number(routeMatch[2]));
}

const sharedMatch = log.match(/^\+\s+First Load JS shared by all\s+([\d.]+)\s+kB\s*$/m);
const failures = [];

if (!sharedMatch) {
  failures.push("Shared First Load JS measurement was not found in the Next.js build log.");
} else {
  const measured = Number(sharedMatch[1]);
  console.log(`shared First Load JS: ${measured} kB / ${budgets.sharedFirstLoadKb} kB`);
  if (measured > budgets.sharedFirstLoadKb) {
    failures.push(`Shared First Load JS is ${measured} kB; budget is ${budgets.sharedFirstLoadKb} kB.`);
  }
}

for (const [route, budget] of Object.entries(budgets.routes)) {
  const measured = routeMeasurements.get(route);
  if (measured === undefined) {
    failures.push(`Route ${route} was not found in the Next.js build log.`);
    continue;
  }
  console.log(`${route}: ${measured} kB / ${budget} kB`);
  if (measured > budget) failures.push(`${route} is ${measured} kB; budget is ${budget} kB.`);
}

// Next emits lazily loaded client chunks as `<id>.<content-hash>.js`.
// Hyphenated files are framework, shared, layout, or route entry chunks and
// are already governed by the shared/route First Load budgets above.
const chunkFiles = (await listJavaScriptFiles(chunkRoot)).filter((filePath) => (
  /^\d+\.[A-Za-z0-9]+\.js$/.test(path.basename(filePath))
));
const chunkMeasurements = await Promise.all(chunkFiles.map(async (filePath) => ({
  filePath,
  gzipKb: gzipSync(await readFile(filePath)).byteLength / 1024,
})));
chunkMeasurements.sort((left, right) => right.gzipKb - left.gzipKb);

for (const chunk of chunkMeasurements.slice(0, 10)) {
  const relativePath = path.relative(projectRoot, chunk.filePath);
  console.log(`${relativePath}: ${chunk.gzipKb.toFixed(1)} kB gzip`);
}

const oversizedChunks = chunkMeasurements.filter((chunk) => chunk.gzipKb > budgets.maxNewClientChunkKb);
for (const chunk of oversizedChunks) {
  failures.push(`${path.relative(projectRoot, chunk.filePath)} is ${chunk.gzipKb.toFixed(1)} kB gzip; client chunk budget is ${budgets.maxNewClientChunkKb} kB.`);
}

if (failures.length) {
  console.error("\nBundle budget verification failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("Bundle budget verification passed.");

async function listJavaScriptFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map((entry) => {
    const entryPath = path.join(directory, entry.name);
    if (entry.isDirectory()) return listJavaScriptFiles(entryPath);
    return entry.isFile() && entry.name.endsWith(".js") ? [entryPath] : [];
  }));
  return nested.flat();
}

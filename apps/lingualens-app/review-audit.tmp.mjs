/* One-off design review audit: walks the 5 therapist surfaces at two
 * viewports, runs an automated battery mapped to the ui-ux-pro-max UX
 * guidelines, and writes findings JSON + per-surface screenshots. */
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const BASE = "http://127.0.0.1:3100";
const SESSION = "session_fb30dfb9fb";
const CASE = "case_2b555d8135";
const OUT_DIR = process.argv[2] || "/tmp/ui-review";

const surfaces = [
  { name: "today", url: "/today" },
  { name: "cases", url: "/cases" },
  { name: "case-detail", url: `/cases/${CASE}` },
  { name: "session-intake", url: `/sessions/${SESSION}?view=intake` },
  { name: "session-transcript", url: `/sessions/${SESSION}?view=transcript` },
  { name: "session-findings", url: `/sessions/${SESSION}?view=findings` },
  { name: "session-report", url: `/sessions/${SESSION}?view=report` },
  { name: "reports", url: "/reports" },
  { name: "settings", url: "/settings?section=account" },
];

const viewports = [
  { name: "mobile", width: 390, height: 844 },
  { name: "desktop", width: 1280, height: 800 },
];

function battery() {
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none";
  };
  const findings = { touchTargets: [], smallText: [], tightLineHeight: [], headingSkips: [], multipleH1: [], iconOnlyButtons: [], emptyLinks: [], missingAlt: [], decorativeAlt: [], overflow: false, lowContrast: [] };

  const interactive = "button, a[href], input, select, textarea, summary, [role='button'], [role='link'], [role='option']";
  document.querySelectorAll(interactive).forEach((el) => {
    if (!visible(el)) return;
    const r = el.getBoundingClientRect();
    if (r.height < 40 || r.width < 40) {
      findings.touchTargets.push({ tag: el.tagName.toLowerCase(), cls: String(el.className || "").slice(0, 60), h: Math.round(r.height), w: Math.round(r.width), text: (el.textContent || "").trim().slice(0, 30) });
    }
  });

  document.querySelectorAll("body *").forEach((el) => {
    if (!visible(el) || !el.childNodes.length) return;
    const hasText = Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim().length > 0);
    if (!hasText) return;
    const cs = getComputedStyle(el);
    const fs = parseFloat(cs.fontSize);
    if (fs > 0 && fs < 12) findings.smallText.push({ cls: String(el.className || "").slice(0, 60), fs, text: el.textContent.trim().slice(0, 30) });
    const lh = parseFloat(cs.lineHeight);
    if (lh > 0 && fs > 0 && lh < fs * 1.35) findings.tightLineHeight.push({ cls: String(el.className || "").slice(0, 60), fs, lh, text: el.textContent.trim().slice(0, 30) });
  });

  const hs = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")].filter(visible);
  const levels = hs.map((h) => Number(h.tagName[1]));
  for (let i = 1; i < levels.length; i++) if (levels[i] > levels[i - 1] + 1) findings.headingSkips.push({ from: levels[i - 1], to: levels[i], text: hs[i].textContent.trim().slice(0, 40) });
  if (levels.filter((l) => l === 1).length > 1) findings.multipleH1.push(levels.filter((l) => l === 1).length);

  document.querySelectorAll("button, [role='button']").forEach((el) => {
    if (!visible(el)) return;
    const text = (el.textContent || "").trim();
    const hasLabel = el.getAttribute("aria-label") || el.getAttribute("title") || el.getAttribute("aria-labelledby");
    if (!text && !hasLabel) findings.iconOnlyButtons.push({ cls: String(el.className || "").slice(0, 60), html: el.outerHTML.slice(0, 120) });
  });

  document.querySelectorAll("a[href]").forEach((el) => {
    if (!visible(el)) return;
    const text = (el.textContent || "").trim();
    const hasLabel = el.getAttribute("aria-label") || el.getAttribute("title") || el.getAttribute("aria-labelledby");
    if (!text && !hasLabel) findings.emptyLinks.push({ cls: String(el.className || "").slice(0, 60), href: String(el.getAttribute("href")).slice(0, 60) });
  });

  document.querySelectorAll("img").forEach((img) => {
    if (!visible(img)) return;
    if (!img.hasAttribute("alt")) findings.missingAlt.push({ src: String(img.getAttribute("src") || "").slice(0, 60), cls: String(img.className || "").slice(0, 40) });
    else if (img.getAttribute("alt") === "" && !img.hasAttribute("aria-hidden") && img.getAttribute("role") !== "presentation") {
      findings.decorativeAlt.push({ src: String(img.getAttribute("src") || "").slice(0, 60) });
    }
  });

  findings.overflow = document.documentElement.scrollWidth > document.documentElement.clientWidth + 1;

  const lum = (hex) => {
    const m = /^#?([0-9a-f]{6})$/i.exec(hex);
    if (!m) return null;
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16) / 255);
    const lin = (c) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  };
  const ratio = (a, b) => { const la = lum(a), lb = lum(b); if (la == null || lb == null) return null; return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05); };
  const toHex = (c) => { const m = /rgba?\(\s*(\d+),\s*(\d+),\s*(\d+)/.exec(c); return m ? "#" + [1, 2, 3].map((i) => Number(m[i]).toString(16).padStart(2, "0")).join("") : c; };
  let checked = 0;
  const seen = new Set();
  document.querySelectorAll("body *").forEach((el) => {
    if (checked > 120 || !visible(el) || el.closest("[aria-hidden='true']")) return;
    const hasText = Array.from(el.childNodes).some((n) => n.nodeType === 3 && n.textContent.trim().length > 0);
    if (!hasText) return;
    const cs = getComputedStyle(el);
    const fs = parseFloat(cs.fontSize);
    if (fs >= 18) return;
    const fg = toHex(cs.color);
    let bg = null;
    for (let n = el; n && n !== document.documentElement; n = n.parentElement) {
      const c = toHex(getComputedStyle(n).backgroundColor);
      if (/^#[0-9a-f]{6}$/i.test(c)) { bg = c; break; }
    }
    if (!bg) return;
    const r = ratio(fg, bg);
    if (r != null && r < 4.5) {
      const key = String(el.className) + "|" + fg + "|" + bg;
      if (!seen.has(key)) { seen.add(key); findings.lowContrast.push({ cls: String(el.className || "").slice(0, 60), fg, bg, ratio: r.toFixed(2), text: el.textContent.trim().slice(0, 30), fs }); }
    }
    checked++;
  });

  return findings;
}

const results = [];
fs.mkdirSync(path.join(OUT_DIR, "screenshots"), { recursive: true });

const browser = await chromium.launch();
for (const viewport of viewports) {
  const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
  const page = await context.newPage();
  await page.addInitScript(() => {
    window.sessionStorage.setItem("lingualens.mock-access-session.v1", JSON.stringify({
      role: "therapist", organizationId: "pilot_org_001", aal: "aal2",
    }));
  });
  page.on("pageerror", (e) => console.error("PAGEERROR", viewport.name, e.message));
  for (const surface of surfaces) {
    await page.goto(BASE + surface.url, { waitUntil: "networkidle" });
    await page.waitForTimeout(400);
    const audit = await page.evaluate(battery);
    await page.screenshot({ path: path.join(OUT_DIR, "screenshots", surface.name + "-" + viewport.name + ".png"), fullPage: true });
    results.push({ surface: surface.name, viewport: viewport.name, url: surface.url, audit });
    const counts = Object.fromEntries(Object.entries(audit).map(([k, v]) => [k, Array.isArray(v) ? v.length : v]));
    console.log(surface.name.padEnd(18), viewport.name.padEnd(8), JSON.stringify(counts));
  }
  await context.close();
}
await browser.close();
fs.writeFileSync(path.join(OUT_DIR, "findings.json"), JSON.stringify(results, null, 2));
console.log("WROTE", path.join(OUT_DIR, "findings.json"));

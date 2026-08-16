/**
 * UI design audit battery: walks a rendered page and reports accessibility /
 * design findings mapped to the ui-ux-pro-max guidelines (priorities 1-10).
 *
 * The function must stay self-contained (no closures over module state) so it
 * can be serialized into `page.evaluate`. It returns a plain findings object;
 * the caller decides which categories are hard gates.
 */
export function uiDesignAuditBattery() {
  const visible = (el: Element) => {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== "hidden" && cs.display !== "none";
  };
  const findings = {
    touchTargets: [] as Array<Record<string, unknown>>,
    smallText: [] as Array<Record<string, unknown>>,
    tightLineHeight: [] as Array<Record<string, unknown>>,
    headingSkips: [] as Array<Record<string, unknown>>,
    multipleH1: [] as Array<Record<string, unknown>>,
    iconOnlyButtons: [] as Array<Record<string, unknown>>,
    emptyLinks: [] as Array<Record<string, unknown>>,
    missingAlt: [] as Array<Record<string, unknown>>,
    decorativeAlt: [] as Array<Record<string, unknown>>,
    overflow: false,
    lowContrast: [] as Array<Record<string, unknown>>,
  };

  const interactive = "button, a[href], input, select, textarea, summary, [role='button'], [role='link'], [role='option']";
  document.querySelectorAll(interactive).forEach((el) => {
    if (!visible(el)) return;
    const r = el.getBoundingClientRect();
    if (r.height < 40 || r.width < 40) {
      findings.touchTargets.push({
        tag: el.tagName.toLowerCase(),
        cls: String(el.className || "").slice(0, 60),
        h: Math.round(r.height),
        w: Math.round(r.width),
        text: (el.textContent || "").trim().slice(0, 30),
      });
    }
  });

  document.querySelectorAll("body *").forEach((el) => {
    if (!visible(el) || !el.childNodes.length) return;
    const hasText = Array.from(el.childNodes).some((n) => n.nodeType === 3 && (n.textContent ?? "").trim().length > 0);
    if (!hasText) return;
    const cs = getComputedStyle(el);
    const fs = parseFloat(cs.fontSize);
    if (fs > 0 && fs < 12) findings.smallText.push({ cls: String(el.className || "").slice(0, 60), fs, text: (el.textContent ?? "").trim().slice(0, 30) });
    const lh = parseFloat(cs.lineHeight);
    if (lh > 0 && fs > 0 && lh < fs * 1.35) findings.tightLineHeight.push({ cls: String(el.className || "").slice(0, 60), fs, lh, text: (el.textContent ?? "").trim().slice(0, 30) });
  });

  const hs = [...document.querySelectorAll("h1,h2,h3,h4,h5,h6")].filter(visible);
  const levels = hs.map((h) => Number(h.tagName[1]));
  for (let i = 1; i < levels.length; i++) {
    if (levels[i] > levels[i - 1] + 1) findings.headingSkips.push({ from: levels[i - 1], to: levels[i], text: (hs[i].textContent ?? "").trim().slice(0, 40) });
  }
  if (levels.filter((l) => l === 1).length > 1) findings.multipleH1.push({ count: levels.filter((l) => l === 1).length });

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

  const lum = (hex: string) => {
    const m = /^#?([0-9a-f]{6})$/i.exec(hex);
    if (!m) return null;
    const [r, g, b] = [0, 2, 4].map((i) => parseInt(m[1].slice(i, i + 2), 16) / 255);
    const lin = (c: number) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
  };
  const ratio = (a: string, b: string) => {
    const la = lum(a), lb = lum(b);
    if (la == null || lb == null) return null;
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  };
  const toHex = (c: string) => {
    const m = /rgba?\(\s*(\d+),\s*(\d+),\s*(\d+)/.exec(c);
    return m ? "#" + [1, 2, 3].map((i) => Number(m[i]).toString(16).padStart(2, "0")).join("") : c;
  };
  let checked = 0;
  const seen = new Set();
  document.querySelectorAll("body *").forEach((el) => {
    if (checked > 120 || !visible(el) || el.closest("[aria-hidden='true']")) return;
    const hasText = Array.from(el.childNodes).some((n) => n.nodeType === 3 && (n.textContent ?? "").trim().length > 0);
    if (!hasText) return;
    const cs = getComputedStyle(el);
    const fs = parseFloat(cs.fontSize);
    if (fs >= 18) return;
    const fg = toHex(cs.color);
    let bg = null;
    for (let n: Element | null = el; n && n !== document.documentElement; n = n.parentElement) {
      const c = toHex(getComputedStyle(n).backgroundColor);
      if (/^#[0-9a-f]{6}$/i.test(c)) { bg = c; break; }
    }
    if (!bg) return;
    const r = ratio(fg, bg);
    if (r != null && r < 4.5) {
      const key = String(el.className) + "|" + fg + "|" + bg;
      if (!seen.has(key)) {
        seen.add(key);
        findings.lowContrast.push({ cls: String(el.className || "").slice(0, 60), fg, bg, ratio: r.toFixed(2), text: (el.textContent ?? "").trim().slice(0, 30), fs });
      }
    }
    checked++;
  });

  return findings;
}

/**
 * The categories that fail the audit (heading hierarchy skips, sub-12px text,
 * icon-only buttons without an accessible label, horizontal overflow). The
 * remaining categories are advisory and reported as evidence only.
 */
export const UI_AUDIT_HARD_GATES = [
  "headingSkips",
  "smallText",
  "iconOnlyButtons",
  "overflow",
] as const;

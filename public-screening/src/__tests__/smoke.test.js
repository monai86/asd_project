import { describe, it, expect } from "vitest";

// Mock localStorage globally for Node testing environment
if (typeof global.localStorage === "undefined") {
  global.localStorage = {
    getItem: () => "th",
    setItem: () => {},
  };
}

import { STRINGS, t } from "../js/i18n.js";

describe("Public Screening i18n Smoke Test", () => {
  it("should have STRINGS defined", () => {
    expect(STRINGS).toBeDefined();
    expect(STRINGS.nav).toBeDefined();
    expect(STRINGS.landing).toBeDefined();
  });

  it("should return the correct translated string for a key", () => {
    expect(t("landing.title")).toContain("คัดกรอง");
  });
});

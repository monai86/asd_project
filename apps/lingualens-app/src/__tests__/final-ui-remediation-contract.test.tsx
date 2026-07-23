import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SettingsNavigation } from "@/features/settings/components/settings-navigation";

function appFile(relative: string): string {
  return readFileSync(resolve(process.cwd(), relative), "utf8");
}

describe("final UI remediation contracts", () => {
  it("keeps the selected-state accent family teal and separate from warning amber", () => {
    const tokens = appFile("src/design-system/tokens.css");

    expect(tokens).toContain("--color-accent-subtle: #4f9fa5;");
    expect(tokens).toContain("--color-warning-text: #92400e;");
    expect(tokens).not.toContain("--color-accent-subtle: #b7791f;");
  });

  it("uses only the LinguaLens design system and Tailwind in the active app foundation", () => {
    const packageManifest = JSON.parse(appFile("package.json")) as {
      dependencies?: Record<string, string>;
      devDependencies?: Record<string, string>;
    };
    const dependencyNames = [
      ...Object.keys(packageManifest.dependencies ?? {}),
      ...Object.keys(packageManifest.devDependencies ?? {}),
    ];
    const globalCss = appFile("src/styles/globals.css");
    const providers = appFile("src/app/providers.tsx");

    expect(dependencyNames.some((name) => name.startsWith("@astryxdesign/"))).toBe(false);
    expect(globalCss).not.toContain("@astryxdesign");
    expect(providers).not.toContain("@astryxdesign");
  });

  it("does not retain unsupported dashboard score primitives", () => {
    const primitives = appFile("src/components/workbench-ui.tsx");

    for (const name of [
      "AppHeader",
      "QuickActionCard",
      "SessionCard",
      "ResultMetricCard",
      "SmallListRow",
      "PrimaryActionRow",
      "ProgressSummaryCard",
    ]) {
      expect(primitives).not.toContain(`function ${name}`);
    }
    expect(primitives).not.toContain("Overall Progress");
    expect(primitives).not.toContain("Pronunciation");
  });

  it("renders mobile Settings as a role-safe category list", () => {
    render(
      <SettingsNavigation
        sections={["account", "organization", "accessibility", "notifications", "privacy", "export", "help"]}
        selected="account"
        onSelect={vi.fn()}
      />,
    );

    const mobileNavigation = screen.getByRole("navigation", { name: "Settings categories mobile" });
    expect(within(mobileNavigation).getByRole("link", { name: /Account/i })).toBeInTheDocument();
    expect(within(mobileNavigation).getByRole("link", { name: /Privacy & Security/i })).toBeInTheDocument();
    expect(within(mobileNavigation).queryByRole("link", { name: /Team/i })).not.toBeInTheDocument();
  });
});

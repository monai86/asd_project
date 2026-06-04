import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const appRoot = resolve(__dirname, "../..");

describe("cross-platform app configuration", () => {
  it("keeps the PWA cache limited to static app-shell assets", () => {
    const viteConfig = readFileSync(resolve(appRoot, "vite.config.js"), "utf8");
    expect(viteConfig).toContain("VitePWA");
    expect(viteConfig).toContain('includeAssets: ["app-icon.svg"]');
    expect(viteConfig).toContain('display: "standalone"');
    expect(viteConfig).toContain("runtimeCaching: []");
    expect(viteConfig).not.toContain("/api/");
  });

  it("configures Capacitor to package the built Vite app for iOS", () => {
    const config = JSON.parse(readFileSync(resolve(appRoot, "capacitor.config.json"), "utf8"));
    expect(config.appId).toBe("com.asdproject.therapist");
    expect(config.webDir).toBe("dist");
    expect(config.ios.contentInset).toBe("automatic");
    expect(config.plugins.PushNotifications.presentationOptions).toContain("alert");
  });

  it("keeps iOS media permission strings tied to consent and signed upload storage", () => {
    const plist = readFileSync(resolve(appRoot, "ios/App/App/Info.plist"), "utf8");
    expect(plist).toContain("NSMicrophoneUsageDescription");
    expect(plist).toContain("guardian consent");
    expect(plist).toContain("private signed-upload storage");
    expect(plist).toContain("NSPhotoLibraryUsageDescription");
  });

  it("uses a native clinical shell around the shared Capacitor workspace", () => {
    const storyboard = readFileSync(resolve(appRoot, "ios/App/App/Base.lproj/Main.storyboard"), "utf8");
    const shellController = readFileSync(resolve(appRoot, "ios/App/App/NativeClinicalShellViewController.swift"), "utf8");

    expect(storyboard).toContain("NativeClinicalShellViewController");
    expect(shellController).toContain("class NativeClinicalShellViewController: CAPBridgeViewController");
    expect(shellController).toContain("native-clinical-shell");
    expect(shellController).not.toContain("case_id");
    expect(shellController).not.toContain("session_id");
  });
});

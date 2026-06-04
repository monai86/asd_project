import { afterEach, describe, expect, it, vi } from "vitest";
import {
  NATIVE_SHELL_EVENT,
  bindNativeShellStatus,
  getNativeShellState
} from "../services/native-shell-service.js";

describe("native clinical shell service", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("detects the shared workspace as a native shell only on native Capacitor platforms", () => {
    vi.stubGlobal("window", {
      Capacitor: { getPlatform: () => "ios" }
    });
    vi.stubGlobal("navigator", { onLine: true });

    const state = getNativeShellState();

    expect(state.platform).toBe("ios");
    expect(state.isNativeShell).toBe(true);
    expect(state.isIOS).toBe(true);
    expect(state.status).toBe("online");
  });

  it("keeps offline state as shell availability, not clinical offline storage", () => {
    const state = getNativeShellState({ platform: "ios", isOnline: false, source: "native" });

    expect(state).toEqual({
      platform: "ios",
      source: "native",
      isNativeShell: true,
      isIOS: true,
      isOnline: false,
      status: "offline"
    });
    expect(JSON.stringify(state)).not.toContain("case_id");
    expect(JSON.stringify(state)).not.toContain("session_id");
  });

  it("accepts native bridge events without requiring a clinical payload", () => {
    const listeners = new Map();
    vi.stubGlobal("window", {
      addEventListener: vi.fn((event, listener) => listeners.set(event, listener)),
      removeEventListener: vi.fn((event) => listeners.delete(event)),
      dispatchEvent: vi.fn()
    });
    vi.stubGlobal("navigator", { onLine: true });
    const onChange = vi.fn();

    const unbind = bindNativeShellStatus(onChange);
    listeners.get(NATIVE_SHELL_EVENT)({
      detail: { platform: "ios", isOnline: false, source: "native-monitor" }
    });
    unbind();

    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({
        platform: "ios",
        isNativeShell: true,
        isOnline: false,
        source: "native-monitor"
      })
    );
    expect(window.removeEventListener).toHaveBeenCalledWith(NATIVE_SHELL_EVENT, expect.any(Function));
  });
});

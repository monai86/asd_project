export const NATIVE_SHELL_EVENT = "native-clinical-shell";

function readCapacitorPlatform() {
  const capacitor = typeof window !== "undefined" ? window.Capacitor : null;
  return capacitor?.getPlatform?.() || "web";
}

function readOnlineStatus() {
  if (typeof navigator === "undefined" || typeof navigator.onLine !== "boolean") {
    return true;
  }
  return navigator.onLine;
}

export function getNativeShellState(overrides = {}) {
  const platform = overrides.platform || readCapacitorPlatform();
  const isOnline = typeof overrides.isOnline === "boolean" ? overrides.isOnline : readOnlineStatus();
  const source = overrides.source || "web";

  return {
    platform,
    source,
    isNativeShell: platform === "ios" || platform === "android",
    isIOS: platform === "ios",
    isOnline,
    status: isOnline ? "online" : "offline"
  };
}

export function publishNativeShellState(state = getNativeShellState()) {
  if (typeof window === "undefined" || typeof window.dispatchEvent !== "function") return;
  window.dispatchEvent(new CustomEvent(NATIVE_SHELL_EVENT, { detail: state }));
}

export function bindNativeShellStatus(onChange) {
  if (typeof window === "undefined") return () => {};

  const emit = (source = "web") => {
    const state = getNativeShellState({ source });
    onChange?.(state);
  };

  const handleOnline = () => emit("web-online");
  const handleOffline = () => emit("web-offline");
  const handleNativeEvent = event => {
    const detail = event?.detail || {};
    const nextState = getNativeShellState({
      platform: detail.platform,
      isOnline: typeof detail.isOnline === "boolean" ? detail.isOnline : undefined,
      source: detail.source || "native"
    });
    onChange?.(nextState);
  };

  window.addEventListener("online", handleOnline);
  window.addEventListener("offline", handleOffline);
  window.addEventListener(NATIVE_SHELL_EVENT, handleNativeEvent);
  emit("web-init");

  return () => {
    window.removeEventListener("online", handleOnline);
    window.removeEventListener("offline", handleOffline);
    window.removeEventListener(NATIVE_SHELL_EVENT, handleNativeEvent);
  };
}

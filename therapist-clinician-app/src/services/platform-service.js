import { getNativeShellState } from "./native-shell-service.js";

export function getClinicalPlatform() {
  const shellState = getNativeShellState();
  const platform = shellState.platform;
  return {
    platform,
    isNative: shellState.isNativeShell,
    isIOS: platform === "ios",
    isWeb: platform === "web",
    isOnline: shellState.isOnline
  };
}

export function getSecureMediaUploadSurface() {
  const platform = getClinicalPlatform();
  if (platform.isIOS) return "ios-capacitor";
  if (platform.isNative) return "native-capacitor";
  return "web";
}

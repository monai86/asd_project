export function getClinicalPlatform() {
  const cap = typeof window !== "undefined" ? window.Capacitor : null;
  const platform = cap?.getPlatform?.() || "web";
  return {
    platform,
    isNative: platform === "ios" || platform === "android",
    isIOS: platform === "ios",
    isWeb: platform === "web"
  };
}

export function getSecureMediaUploadSurface() {
  const platform = getClinicalPlatform();
  if (platform.isIOS) return "ios-capacitor";
  if (platform.isNative) return "native-capacitor";
  return "web";
}

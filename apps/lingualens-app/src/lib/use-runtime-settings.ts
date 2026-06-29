"use client";

import { useEffect, useState } from "react";

import { getRuntimeSettings, type RuntimeSettings } from "@/lib/api";

export function useRuntimeSettings() {
  const [runtimeSettings, setRuntimeSettings] = useState<RuntimeSettings | null>(null);

  useEffect(() => {
    let cancelled = false;
    void getRuntimeSettings()
      .then((settings) => {
        if (!cancelled) setRuntimeSettings(settings);
      })
      .catch(() => {
        if (!cancelled) setRuntimeSettings(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return runtimeSettings;
}

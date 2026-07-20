"use client";

import { useEffect, useState } from "react";

import { getRuntimeSettings, type RuntimeSettings } from "@/lib/api";
import { confirmed, type RemoteState } from "@/services/adapters/remote-state";

let runtimeSettingsRequest: Promise<RuntimeSettings> | null = null;

function loadRuntimeSettings(): Promise<RuntimeSettings> {
  if (!runtimeSettingsRequest) {
    runtimeSettingsRequest = getRuntimeSettings().catch((error: unknown) => {
      runtimeSettingsRequest = null;
      throw error;
    });
  }
  return runtimeSettingsRequest;
}

export function resetRuntimeSettingsCache(): void {
  runtimeSettingsRequest = null;
}

export function useRuntimeSettings(): RemoteState<RuntimeSettings> {
  const [runtimeSettings, setRuntimeSettings] = useState<RemoteState<RuntimeSettings>>({
    status: "loading",
    mode: "backend",
  });

  useEffect(() => {
    let cancelled = false;
    void loadRuntimeSettings()
      .then((settings) => {
        if (!cancelled) setRuntimeSettings(confirmed(settings));
      })
      .catch(() => {
        if (!cancelled) {
          setRuntimeSettings({
            status: "error",
            mode: "backend",
            message: "Runtime settings unavailable",
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return runtimeSettings;
}

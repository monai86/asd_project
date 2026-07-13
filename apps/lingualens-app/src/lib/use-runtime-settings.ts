"use client";

import { useEffect, useState } from "react";

import { getRuntimeSettings, type RuntimeSettings } from "@/lib/api";
import { confirmed, type RemoteState } from "@/services/adapters/remote-state";

export function useRuntimeSettings(): RemoteState<RuntimeSettings> {
  const [runtimeSettings, setRuntimeSettings] = useState<RemoteState<RuntimeSettings>>({
    status: "loading",
    mode: "backend",
  });

  useEffect(() => {
    let cancelled = false;
    void getRuntimeSettings()
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

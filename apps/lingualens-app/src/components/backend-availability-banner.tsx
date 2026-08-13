"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { WifiOff } from "lucide-react";

import { checkBackendAvailability } from "@/lib/api";

export function useBackendAvailability() {
  const [backendUnavailable, setBackendUnavailable] = useState(false);
  const explicitAvailability = useRef<boolean | undefined>(undefined);
  const setExplicitBackendUnavailable = useCallback((unavailable: boolean) => {
    explicitAvailability.current = unavailable;
    setBackendUnavailable(unavailable);
  }, []);

  useEffect(() => {
    let cancelled = false;
    void checkBackendAvailability().then((available) => {
      if (!cancelled && explicitAvailability.current === undefined) {
        setBackendUnavailable(!available);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return { backendUnavailable, setBackendUnavailable: setExplicitBackendUnavailable };
}

export function BackendAvailabilityBanner({ unavailable }: { unavailable: boolean }) {
  if (!unavailable) return null;
  return (
    <div className="mb-5 rounded-[var(--radius-panel)] border border-amber-300 bg-amber-50 p-4 text-amber-950" role="status">
      <div className="flex items-start gap-3">
        <WifiOff className="mt-0.5 shrink-0" size={20} aria-hidden="true" />
        <div>
          <p className="font-bold">Backend unavailable — local workspace mode</p>
          <p className="mt-1 text-sm">Changes are stored locally only and may not persist across devices or server restarts.</p>
        </div>
      </div>
    </div>
  );
}

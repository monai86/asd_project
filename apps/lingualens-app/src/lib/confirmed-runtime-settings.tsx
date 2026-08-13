"use client";

import { createContext, useContext } from "react";

import type { RuntimeSettings } from "@/lib/api";

const ConfirmedRuntimeSettingsContext = createContext<RuntimeSettings | null>(null);

export function ConfirmedRuntimeSettingsProvider({
  children,
  value,
}: {
  children: React.ReactNode;
  value: RuntimeSettings;
}) {
  return (
    <ConfirmedRuntimeSettingsContext.Provider value={value}>
      {children}
    </ConfirmedRuntimeSettingsContext.Provider>
  );
}

export function useConfirmedRuntimeSettings(): RuntimeSettings | null {
  return useContext(ConfirmedRuntimeSettingsContext);
}

"use client";

import { useCallback, useMemo, useState } from "react";

import type { TodayWorkbenchViewState } from "@/features/work-queue/components/today-workbench-view";
import { todayWorkbenchAdapter, type TodayWorkbenchPayload } from "@/features/work-queue/services/today-workbench-adapter";
import { buildTodayWorkbench } from "@/features/work-queue/today-workbench-model";
import { useRemoteResource } from "@/services/adapters/use-remote-resource";

async function loadTodayWorkbench(_identity: string, signal: AbortSignal): Promise<TodayWorkbenchPayload> {
  return todayWorkbenchAdapter.load(signal);
}

export function useTodayWorkbench(): TodayWorkbenchViewState {
  const [requestVersion, setRequestVersion] = useState(0);
  const resource = useRemoteResource(`today:${requestVersion}`, loadTodayWorkbench);
  const retry = useCallback(() => setRequestVersion((current) => current + 1), []);
  const model = useMemo(() => {
    if (resource.status !== "success" && resource.status !== "stale") return null;
    return buildTodayWorkbench(resource.data.cases, resource.data.reports);
  }, [resource]);

  if (resource.status === "error" || resource.status === "unavailable") return { status: "error", retry };
  if (!model) return { status: "loading" };
  return { status: "ready", model };
}

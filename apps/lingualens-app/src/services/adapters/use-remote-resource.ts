"use client";

import { useEffect, useRef, useState } from "react";

import {
  confirmed,
  failedWithPrevious,
  type RemoteState,
} from "@/services/adapters/remote-state";

type RemoteLoader<T> = (identity: string, signal: AbortSignal) => Promise<T>;

function previousData<T>(state: RemoteState<T>): T | undefined {
  if ("data" in state) {
    return state.data;
  }
  if ("previous" in state) {
    return state.previous;
  }
  return undefined;
}

export function useRemoteResource<T>(
  identity: string,
  load: RemoteLoader<T>,
): RemoteState<T> {
  const requestId = useRef(0);
  const [state, setState] = useState<RemoteState<T>>({
    status: "loading",
    mode: "backend",
  });

  useEffect(() => {
    const controller = new AbortController();
    const currentRequest = ++requestId.current;

    setState((previous) => ({
      status: "loading",
      mode: "backend",
      previous: previousData(previous),
    }));

    void (async () => {
      try {
        const data = await load(identity, controller.signal);
        if (currentRequest === requestId.current && !controller.signal.aborted) {
          setState(confirmed(data));
        }
      } catch (error: unknown) {
        if (currentRequest === requestId.current && !controller.signal.aborted) {
          setState((previous) =>
            failedWithPrevious(error, previousData(previous)),
          );
        }
      }
    })();

    return () => {
      controller.abort();
      if (requestId.current === currentRequest) {
        requestId.current += 1;
      }
    };
  }, [identity, load]);

  return state;
}

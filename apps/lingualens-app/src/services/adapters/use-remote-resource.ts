"use client";

import { useEffect, useRef, useState } from "react";

import {
  confirmed,
  failedWithPrevious,
  type RemoteState,
} from "@/services/adapters/remote-state";

type RemoteLoader<T> = (identity: string, signal: AbortSignal) => Promise<T>;
type OwnedRemoteState<T> = { identity: string; state: RemoteState<T> };

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
  const latestLoad = useRef(load);
  latestLoad.current = load;
  const [resource, setResource] = useState<OwnedRemoteState<T>>({
    identity,
    state: { status: "loading", mode: "backend" },
  });

  useEffect(() => {
    const controller = new AbortController();
    const currentRequest = ++requestId.current;

    setResource((previous) => {
      const previousForIdentity =
        previous.identity === identity ? previousData(previous.state) : undefined;
      return {
        identity,
        state: {
          status: "loading",
          mode: "backend",
          ...(previousForIdentity === undefined
            ? {}
            : { previous: previousForIdentity }),
        },
      };
    });

    void (async () => {
      try {
        const data = await latestLoad.current(identity, controller.signal);
        if (currentRequest === requestId.current && !controller.signal.aborted) {
          setResource({ identity, state: confirmed(data) });
        }
      } catch (error: unknown) {
        if (currentRequest === requestId.current && !controller.signal.aborted) {
          setResource((previous) => ({
            identity,
            state: failedWithPrevious(
              error,
              previous.identity === identity
                ? previousData(previous.state)
                : undefined,
            ),
          }));
        }
      }
    })();

    return () => {
      controller.abort();
      if (requestId.current === currentRequest) {
        requestId.current += 1;
      }
    };
    // A request lifetime belongs to an identity. Recreating a loader function
    // is not an implicit refresh; callers refresh by changing the identity.
  }, [identity]);

  return resource.identity === identity
    ? resource.state
    : { status: "loading", mode: "backend" };
}

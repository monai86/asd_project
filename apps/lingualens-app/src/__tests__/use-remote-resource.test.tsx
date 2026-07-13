import { act, renderHook, waitFor } from "@testing-library/react";
import { expect, test, vi } from "vitest";

import { useRemoteResource } from "@/services/adapters/use-remote-resource";

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });

  return { promise, resolve, reject };
}

test("ignores a response for the previous session identity", async () => {
  const first = deferred<string>();
  const second = deferred<string>();
  const load = vi.fn((key: string, _signal: AbortSignal) =>
    key === "one" ? first.promise : second.promise,
  );
  const { result, rerender } = renderHook(
    ({ identity }) => useRemoteResource(identity, load),
    { initialProps: { identity: "one" } },
  );

  rerender({ identity: "two" });
  second.resolve("new");
  await waitFor(() =>
    expect(result.current).toMatchObject({ status: "success", data: "new" }),
  );

  first.resolve("old");
  await act(async () => Promise.resolve());

  expect(result.current).toMatchObject({ status: "success", data: "new" });
});

test("aborts the previous request when the identity changes", () => {
  const pending = deferred<string>();
  const signals: AbortSignal[] = [];
  const load = vi.fn((_identity: string, signal: AbortSignal) => {
    signals.push(signal);
    return pending.promise;
  });
  const { rerender } = renderHook(
    ({ identity }) => useRemoteResource(identity, load),
    { initialProps: { identity: "one" } },
  );

  expect(signals[0]?.aborted).toBe(false);
  rerender({ identity: "two" });

  expect(signals[0]?.aborted).toBe(true);
  expect(signals[1]?.aborted).toBe(false);
});

test("aborts safely on unmount without publishing an error", async () => {
  const pending = deferred<string>();
  let signal: AbortSignal | undefined;
  const load = vi.fn((_identity: string, requestSignal: AbortSignal) => {
    signal = requestSignal;
    return pending.promise;
  });
  const { result, unmount } = renderHook(() => useRemoteResource("one", load));

  unmount();
  expect(signal?.aborted).toBe(true);

  pending.reject(new DOMException("Aborted", "AbortError"));
  await act(async () => Promise.resolve());

  expect(result.current).toMatchObject({ status: "loading", mode: "backend" });
});

test("does not let a stale error replace a newer success", async () => {
  const first = deferred<string>();
  const second = deferred<string>();
  const load = vi.fn((key: string, _signal: AbortSignal) =>
    key === "one" ? first.promise : second.promise,
  );
  const { result, rerender } = renderHook(
    ({ identity }) => useRemoteResource(identity, load),
    { initialProps: { identity: "one" } },
  );

  rerender({ identity: "two" });
  second.resolve("new");
  await waitFor(() =>
    expect(result.current).toMatchObject({ status: "success", data: "new" }),
  );

  first.reject(new Error("old request failed"));
  await act(async () => Promise.resolve());

  expect(result.current).toMatchObject({ status: "success", data: "new" });
});

test("does not duplicate a request for an unrelated rerender", () => {
  const pending = deferred<string>();
  const load = vi.fn((_identity: string, _signal: AbortSignal) => pending.promise);
  const { rerender } = renderHook(
    ({ identity, renderCount }) => {
      void renderCount;
      return useRemoteResource(identity, load);
    },
    { initialProps: { identity: "one", renderCount: 1 } },
  );

  rerender({ identity: "one", renderCount: 2 });

  expect(load).toHaveBeenCalledTimes(1);
});

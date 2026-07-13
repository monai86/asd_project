export type DataMode = "backend" | "sample" | "local-draft" | "unavailable";

export type StaleCause = "transcript-edited" | "report-revised" | "session-changed";

export type RemoteState<T> =
  | { status: "idle"; mode: DataMode }
  | { status: "loading"; mode: DataMode; previous?: T }
  | { status: "success"; mode: DataMode; data: T }
  | { status: "empty"; mode: DataMode }
  | { status: "error"; mode: DataMode; message: string; previous?: T }
  | { status: "unavailable"; mode: "unavailable"; reason: string }
  | { status: "stale"; mode: DataMode; data: T; invalidatedBy: StaleCause };

export const confirmed = <T>(data: T, mode: DataMode = "backend"): RemoteState<T> =>
  Array.isArray(data) && data.length === 0
    ? { status: "empty", mode }
    : { status: "success", mode, data };

export const failedWithPrevious = <T>(error: Error, previous?: T): RemoteState<T> => ({
  status: "error",
  mode: "backend",
  message: error.message || "Request failed",
  previous,
});

export const stale = <T>(data: T, invalidatedBy: StaleCause): RemoteState<T> => ({
  status: "stale",
  mode: "backend",
  data,
  invalidatedBy,
});

export type DataMode = "backend" | "sample" | "local-draft" | "unavailable";
export type AvailableDataMode = Exclude<DataMode, "unavailable">;

export type StaleCause = "transcript-edited" | "report-revised" | "session-changed";

export type RemoteState<T> =
  | { status: "idle"; mode: AvailableDataMode }
  | { status: "loading"; mode: AvailableDataMode; previous?: T }
  | { status: "success"; mode: AvailableDataMode; data: T }
  | { status: "empty"; mode: AvailableDataMode }
  | { status: "error"; mode: AvailableDataMode; message: string; previous?: T }
  | { status: "unavailable"; mode: "unavailable"; reason: string }
  | { status: "stale"; mode: AvailableDataMode; data: T; invalidatedBy: StaleCause };

export const confirmed = <T>(data: T, mode: AvailableDataMode = "backend"): RemoteState<T> =>
  Array.isArray(data) && data.length === 0
    ? { status: "empty", mode }
    : { status: "success", mode, data };

export const failedWithPrevious = <T>(
  _error: unknown,
  previous?: T,
  mode: AvailableDataMode = "backend",
): RemoteState<T> => ({
  status: "error",
  mode,
  message: "Request failed",
  previous,
});

export const stale = <T>(
  data: T,
  invalidatedBy: StaleCause,
  mode: AvailableDataMode = "backend",
): RemoteState<T> => ({
  status: "stale",
  mode,
  data,
  invalidatedBy,
});

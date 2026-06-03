import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import {
  ApiClientConfigurationError,
  ApiClientRequestError,
  createApiClient,
  api
} from "../services/api-client.js";
import { store } from "../store/state.js";

describe("API client boundary", () => {
  it("fails closed when the backend API base URL is not configured", async () => {
    const client = createApiClient({ fetchImpl: vi.fn() });

    await expect(client.get("/api/me")).rejects.toThrow(ApiClientConfigurationError);
  });

  it("sends JSON requests with bearer auth when a token provider is configured", async () => {
    const fetchImpl = vi.fn(async () => ({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ ok: true })
    }));
    const client = createApiClient({
      baseUrl: "https://api.example.test/",
      getToken: async () => "session-token",
      fetchImpl
    });

    const result = await client.post("/api/cases", { anonymized_child_code: "CHI-A" });

    expect(result).toEqual({ ok: true });
    expect(fetchImpl).toHaveBeenCalledWith("https://api.example.test/api/cases", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: "Bearer session-token"
      },
      body: JSON.stringify({ anonymized_child_code: "CHI-A" })
    });
  });

  it("throws request errors with status and parsed payload", async () => {
    const client = createApiClient({
      baseUrl: "https://api.example.test",
      fetchImpl: vi.fn(async () => ({
        ok: false,
        status: 403,
        text: async () => JSON.stringify({ detail: "Access denied." })
      }))
    });

    await expect(client.get("/api/cases")).rejects.toMatchObject({
      name: "ApiClientRequestError",
      status: 403,
      payload: { detail: "Access denied." }
    });
    await expect(client.get("/api/cases")).rejects.toThrow(ApiClientRequestError);
  });
});

describe("API client singleton", () => {
  let originalFetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    store.setState({ currentUser: null });
  });

  it("is instantiated correctly as a singleton", () => {
    expect(api).toBeDefined();
    expect(typeof api.get).toBe("function");
    expect(typeof api.post).toBe("function");
    expect(typeof api.put).toBe("function");
    expect(typeof api.patch).toBe("function");
  });

  it("dynamically adds X-User-Id header when a user is signed in", async () => {
    const mockFetch = vi.fn(async () => ({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ success: true })
    }));
    globalThis.fetch = mockFetch;

    store.setState({ currentUser: { user_id: "user_therapist_001" } });

    const result = await api.get("/api/test");
    expect(result).toEqual({ success: true });
    expect(mockFetch).toHaveBeenCalled();
    const [url, options] = mockFetch.mock.calls[0];
    expect(options.headers).toHaveProperty("X-User-Id", "user_therapist_001");
  });

  it("omits X-User-Id header when user is signed out", async () => {
    const mockFetch = vi.fn(async () => ({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ success: true })
    }));
    globalThis.fetch = mockFetch;

    store.setState({ currentUser: null });

    const result = await api.get("/api/test");
    expect(result).toEqual({ success: true });
    expect(mockFetch).toHaveBeenCalled();
    const [url, options] = mockFetch.mock.calls[0];
    expect(options.headers).not.toHaveProperty("X-User-Id");
  });
});


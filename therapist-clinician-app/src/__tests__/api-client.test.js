import { describe, expect, it, vi } from "vitest";
import {
  ApiClientConfigurationError,
  ApiClientRequestError,
  createApiClient
} from "../services/api-client.js";

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

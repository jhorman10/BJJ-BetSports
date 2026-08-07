import { afterEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "./client";
import { APP_CONFIG } from "../../config/constants";
import type { InternalAxiosRequestConfig } from "axios";

// Mirror the factory's baseURL resolution so the assertion is env-agnostic
const EXPECTED_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// The request interceptor is registered inside createApiClient(); invoke its
// handler directly with a minimal config (no mock adapter, no new deps).
const requestHandler = (
  apiClient.interceptors.request as unknown as {
    handlers: Array<{
      fulfilled: (
        config: InternalAxiosRequestConfig
      ) => InternalAxiosRequestConfig;
    }>;
  }
).handlers[0].fulfilled;

// Fresh config per test so header mutations cannot leak between scenarios.
const createConfig = () =>
  ({ headers: {} }) as InternalAxiosRequestConfig;

describe("apiClient (canonical instance)", () => {
  it("uses the canonical baseURL from the environment or localhost default", () => {
    expect(apiClient.defaults.baseURL).toBe(EXPECTED_BASE_URL);
  });

  it("uses the centralized default timeout from APP_CONFIG", () => {
    expect(apiClient.defaults.timeout).toBe(APP_CONFIG.API_DEFAULT_TIMEOUT);
  });

  it("sends JSON content type by default", () => {
    expect(apiClient.defaults.headers["Content-Type"]).toBe("application/json");
  });
});

describe("apiClient request interceptor (X-API-Key)", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("injects X-API-Key when VITE_ADMIN_API_KEY is set", () => {
    vi.stubEnv("VITE_ADMIN_API_KEY", "test-key");

    const config = requestHandler(createConfig());

    expect(config.headers["X-API-Key"]).toBe("test-key");
  });

  it("omits X-API-Key when VITE_ADMIN_API_KEY is unset", () => {
    vi.stubEnv("VITE_ADMIN_API_KEY", "");

    const config = requestHandler(createConfig());

    expect(config.headers["X-API-Key"]).toBeUndefined();
  });

  it("omits X-API-Key when VITE_ADMIN_API_KEY is blank or whitespace", () => {
    vi.stubEnv("VITE_ADMIN_API_KEY", "   ");

    const config = requestHandler(createConfig());

    expect(config.headers["X-API-Key"]).toBeUndefined();
  });
});

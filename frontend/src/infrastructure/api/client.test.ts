import { describe, expect, it } from "vitest";
import { apiClient } from "./client";
import { APP_CONFIG } from "../../config/constants";

// Mirror the factory's baseURL resolution so the assertion is env-agnostic
const EXPECTED_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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

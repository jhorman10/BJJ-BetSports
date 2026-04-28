import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../services/api", () => ({
  api: {
    healthCheck: vi.fn(),
  },
}));

import { api } from "../../services/api";
import { useOfflineStore } from "./useOfflineStore";

const mockedHealthCheck = vi.mocked(api.healthCheck);

describe("useOfflineStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useOfflineStore.setState({
      isOnline: true,
      isBackendAvailable: true,
      lastSync: null,
    });
  });

  it("recovers from a false offline signal when backend health responds", async () => {
    Object.defineProperty(window.navigator, "onLine", {
      configurable: true,
      value: false,
    });
    mockedHealthCheck.mockResolvedValue({
      status: "ok",
      version: "test",
      timestamp: new Date().toISOString(),
    });

    await useOfflineStore.getState().checkConnectivity();

    const state = useOfflineStore.getState();
    expect(state.isOnline).toBe(true);
    expect(state.isBackendAvailable).toBe(true);
  });

  it("keeps internet on but marks backend unavailable when health check fails", async () => {
    Object.defineProperty(window.navigator, "onLine", {
      configurable: true,
      value: true,
    });
    mockedHealthCheck.mockRejectedValue(new Error("backend down"));

    await useOfflineStore.getState().checkConnectivity();

    const state = useOfflineStore.getState();
    expect(state.isOnline).toBe(true);
    expect(state.isBackendAvailable).toBe(false);
  });
});
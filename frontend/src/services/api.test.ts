import { describe, expect, it, vi } from "vitest";

import { API_ENDPOINTS } from "../config/constants";
import { apiClient } from "../infrastructure/api/client";
import { BestCombinationResponse } from "../types";

import api from "./api";

vi.mock("../infrastructure/api/client", () => ({
  apiClient: { post: vi.fn(), get: vi.fn() },
}));

describe("api.getBestCombination", () => {
  it("posts to the best-combination endpoint with the provided filters", async () => {
    const payload = { data: {} as BestCombinationResponse };
    vi.mocked(apiClient.post).mockResolvedValue(payload);

    await api.getBestCombination({
      min_probability: 0.6,
      exclude_leagues: ["E0"],
    });

    expect(apiClient.post).toHaveBeenCalledWith(
      API_ENDPOINTS.BEST_COMBINATION,
      { min_probability: 0.6, exclude_leagues: ["E0"] }
    );
  });

  it("sends an empty object body when no filters are provided", async () => {
    const payload = { data: {} as BestCombinationResponse };
    vi.mocked(apiClient.post).mockResolvedValue(payload);

    await api.getBestCombination();

    expect(apiClient.post).toHaveBeenCalledWith(
      API_ENDPOINTS.BEST_COMBINATION,
      {}
    );
  });

  it("returns response.data from the POST", async () => {
    const response: BestCombinationResponse = {
      legs: [],
      aggregate: {
        total_probability: 0.5,
        total_odds: 2.0,
        expected_value: 0.0,
        mixed_odds: false,
      },
      stake: { suggested_stake_pct: 0.01, risk_level: 1, kelly_fraction: 0.25 },
      generated_at: "2026-09-08T10:00:00Z",
      independence_disclaimer: "",
      warnings: [],
    };
    vi.mocked(apiClient.post).mockResolvedValue({ data: response });

    const result = await api.getBestCombination();

    expect(result).toBe(response);
  });
});
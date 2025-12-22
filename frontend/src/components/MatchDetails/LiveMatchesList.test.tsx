import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useLiveMatches } from "../../hooks/useLiveMatches";
import api from "../../services/api";

vi.mock("../../services/api", () => ({
  default: {
    getLiveMatches: vi.fn(),
  },
}));

describe("useLiveMatches Hook", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches live matches successfully", async () => {
    const mockMatches = [
      { id: "1", home_team: "Team A", away_team: "Team B", status: "LIVE" },
    ];

    // Mock API response
    (api.getLiveMatches as any).mockResolvedValue(mockMatches);

    const { result } = renderHook(() => useLiveMatches());

    expect(result.current.loading).toBe(true);

    // Wait for update
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Check if data is loaded (Note: loop maps it to internal structure)
    expect(result.current.matches.length).toBeGreaterThan(0);
    expect(result.current.matches[0].home_team).toBe("Team A");
  });

  it("handles API errors gracefully by using mocks/fallback", async () => {
    (api.getLiveMatches as any).mockRejectedValue(new Error("API Error"));

    const { result } = renderHook(() => useLiveMatches());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    // Should have fallen back to mocks
    expect(result.current.matches.length).toBeGreaterThan(0);
  });
});

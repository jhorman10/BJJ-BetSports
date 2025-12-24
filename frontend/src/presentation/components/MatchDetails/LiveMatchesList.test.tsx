import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useLiveMatches } from "../../../hooks/useLiveMatches";
import api from "../../../services/api";

vi.mock("../../../services/api", () => {
  return {
    __esModule: true,
    api: {
      getLiveMatches: vi.fn(),
    },
    default: {
      getLiveMatches: vi.fn(),
    },
  };
});

// Mock global fetch
global.fetch = vi.fn().mockResolvedValue({
  ok: true,
  json: async () => ({
    leagues: [{ name: "Test League", slug: "test-league" }],
    events: [
      {
        id: "test-event",
        status: { type: { state: "in" }, displayClock: "10'" },
        competitions: [
          {
            competitors: [
              {
                homeAway: "home",
                team: { id: "1", displayName: "Home" },
                score: "1",
              },
              {
                homeAway: "away",
                team: { id: "2", displayName: "Away" },
                score: "0",
              },
            ],
          },
        ],
      },
    ],
  }),
});

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

    // Increased timeout to account for batch processing delays
    await waitFor(
      () => {
        expect(result.current.loading).toBe(false);
      },
      { timeout: 10000 }
    );

    // Should have fallen back to mocks
    expect(result.current.matches.length).toBeGreaterThan(0);
  });
});

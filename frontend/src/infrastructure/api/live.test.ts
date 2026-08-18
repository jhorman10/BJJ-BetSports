import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  LiveMatchPrediction,
  Match,
  MatchPrediction,
  Prediction,
} from "../../domain/entities";

const mocks = vi.hoisted(() => ({
  fetchESPNLiveMatches: vi.fn(),
  apiGet: vi.fn(),
}));

vi.mock("../external/espn", () => ({
  fetchESPNLiveMatches: mocks.fetchESPNLiveMatches,
}));

vi.mock("./client", () => ({
  apiClient: { get: mocks.apiGet },
}));

import { liveApi } from "./live";

const makePrediction = (matchId: string): Prediction => ({
  match_id: matchId,
  home_win_probability: 0.6,
  draw_probability: 0.2,
  away_win_probability: 0.2,
  over_25_probability: 0.5,
  under_25_probability: 0.5,
  predicted_home_goals: 1.5,
  predicted_away_goals: 0.8,
  confidence: 0.6,
  data_sources: ["Rigorous ML"],
  recommended_bet: "N/A",
  over_under_recommendation: "N/A",
  created_at: "2026-08-11T10:00:00Z",
});

const backendPrediction = (
  overrides: Partial<Match> = {}
): MatchPrediction => ({
  match: {
    id: "backend-1",
    home_team: { id: "h1", name: "Real Madrid" },
    away_team: { id: "a1", name: "Barcelona" },
    league: { id: "esp.1", name: "La Liga", country: "Spain" },
    match_date: "2026-08-11T19:00:00Z",
    home_goals: 1,
    away_goals: 0,
    status: "FT",
    minute: "99'",
    home_corners: 4,
    away_corners: 2,
    home_yellow_cards: 3,
    away_yellow_cards: 2,
    home_red_cards: 0,
    away_red_cards: 0,
    home_total_shots: 12,
    away_total_shots: 8,
    home_shots_on_target: 5,
    away_shots_on_target: 3,
    home_fouls: 9,
    away_fouls: 11,
    home_offsides: 2,
    away_offsides: 1,
    home_possession: "58%",
    away_possession: "42%",
    home_odds: 1.8,
    draw_odds: 3.4,
    away_odds: 4.2,
    home_spi: 78.5,
    away_spi: 71.2,
    events: [
      { time: "3'", team_id: "h1", player_name: "P1", type: "goal", detail: "" },
    ],
    ...overrides,
  },
  prediction: makePrediction("backend-1"),
});

const espnMatch = (overrides: Partial<Match> = {}): LiveMatchPrediction => ({
  match: {
    id: "401903297",
    home_team: { id: "h1", name: "Real Madrid" },
    away_team: { id: "a1", name: "Barcelona" },
    league: { id: "esp.1", name: "La Liga", country: "Spain" },
    match_date: "2026-08-11T20:00:00Z",
    home_goals: 1,
    away_goals: 0,
    status: "LIVE",
    minute: "11'",
    home_corners: 1,
    away_corners: 0,
    home_yellow_cards: 0,
    away_yellow_cards: 1,
    home_red_cards: 0,
    away_red_cards: 0,
    home_total_shots: 6,
    away_total_shots: 4,
    home_shots_on_target: 2,
    away_shots_on_target: 1,
    home_fouls: 4,
    away_fouls: 5,
    home_offsides: 0,
    away_offsides: 0,
    home_possession: "55%",
    away_possession: "45%",
    ...overrides,
  },
  prediction: makePrediction("401903297"),
  isProcessing: true,
});

describe("liveApi.getLiveMatchesWithPredictions merge", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("keeps ESPN stats (incl. genuine 0) and ESPN minute/status when backend also has data", async () => {
    mocks.apiGet.mockResolvedValue({ data: [backendPrediction()] });
    mocks.fetchESPNLiveMatches.mockResolvedValue([espnMatch()]);

    const merged = await liveApi.getLiveMatchesWithPredictions(false);

    expect(merged).toHaveLength(1);
    const match = merged[0].match;
    // ESPN wins over backend values (corners 4/2, yellows 3/2 in backend)
    expect(match.home_corners).toBe(1);
    expect(match.away_corners).toBe(0);
    expect(match.home_yellow_cards).toBe(0);
    expect(match.away_yellow_cards).toBe(1);
    // Minute/status always come from ESPN, not the backend doc
    expect(match.minute).toBe("11'");
    expect(match.status).toBe("LIVE");
    // Backend prediction survives the merge
    expect(merged[0].prediction.home_win_probability).toBe(0.6);
    expect(merged[0].isProcessing).toBe(false);
  });

  it("fills only ESPN gaps with backend values", async () => {
    const espnWithoutFouls = espnMatch({
      home_fouls: undefined,
      away_fouls: undefined,
    });
    mocks.apiGet.mockResolvedValue({ data: [backendPrediction()] });
    mocks.fetchESPNLiveMatches.mockResolvedValue([espnWithoutFouls]);

    const merged = await liveApi.getLiveMatchesWithPredictions(false);

    const match = merged[0].match;
    // Backend fills the gap ESPN does not provide
    expect(match.home_fouls).toBe(9);
    expect(match.away_fouls).toBe(11);
    // Every stat ESPN provides keeps the ESPN value
    expect(match.home_corners).toBe(1);
    expect(match.away_corners).toBe(0);
    expect(match.home_total_shots).toBe(6);
    expect(match.home_possession).toBe("55%");
  });

  it("keeps backend-only fields (odds, spi, events) on the merged match", async () => {
    mocks.apiGet.mockResolvedValue({ data: [backendPrediction()] });
    mocks.fetchESPNLiveMatches.mockResolvedValue([espnMatch()]);

    const merged = await liveApi.getLiveMatchesWithPredictions(false);

    const match = merged[0].match;
    expect(match.home_odds).toBe(1.8);
    expect(match.home_spi).toBe(78.5);
    expect(match.events).toHaveLength(1);
  });

  it("returns ESPN matches only when the backend request fails", async () => {
    mocks.apiGet.mockRejectedValue(new Error("network down"));
    mocks.fetchESPNLiveMatches.mockResolvedValue([espnMatch()]);

    const merged = await liveApi.getLiveMatchesWithPredictions(false);

    expect(merged).toHaveLength(1);
    expect(merged[0].match.id).toBe("401903297");
    expect(merged[0].match.home_corners).toBe(1);
    // No zero-stubs or fabricated stats are injected for missing values
    expect(merged[0].match.home_offsides).toBe(0);
    expect(merged[0].match.home_fouls).toBe(4);
  });

  it("keeps ESPN gaps undefined when backend is unavailable", async () => {
    const espnWithoutOffsides = espnMatch({
      home_offsides: undefined,
      away_offsides: undefined,
    });
    mocks.apiGet.mockRejectedValue(new Error("network down"));
    mocks.fetchESPNLiveMatches.mockResolvedValue([espnWithoutOffsides]);

    const merged = await liveApi.getLiveMatchesWithPredictions(false);

    expect(merged).toHaveLength(1);
    expect(merged[0].match.home_offsides).toBeUndefined();
    expect(merged[0].match.away_offsides).toBeUndefined();
  });

  it("returns an empty list when ESPN has no live matches", async () => {
    mocks.apiGet.mockResolvedValue({ data: [backendPrediction()] });
    mocks.fetchESPNLiveMatches.mockResolvedValue([]);

    const merged = await liveApi.getLiveMatchesWithPredictions(false);

    expect(merged).toEqual([]);
  });
});

import { describe, expect, it } from "vitest";

import { LiveMatchPrediction } from "../domain/entities";

import { toLiveMatch } from "./useLiveMatches";

/** Builds a full ESPN LiveMatchPrediction with overridable match fields. */
const makeEspnMatch = (
  overrides: Partial<LiveMatchPrediction["match"]> = {}
): LiveMatchPrediction => ({
  match: {
    id: "event-1",
    home_team: { id: "1", name: "Home FC", logo_url: "h.png" },
    away_team: { id: "2", name: "Away FC", logo_url: "a.png" },
    league: { id: "eng.1", name: "Premier League", country: "" },
    match_date: "2026-08-05T00:00:00.000Z",
    home_goals: 2,
    away_goals: 1,
    status: "LIVE",
    minute: "45:00",
    home_corners: 4,
    away_corners: 3,
    home_yellow_cards: 1,
    away_yellow_cards: 2,
    home_red_cards: 0,
    away_red_cards: 1,
    ...overrides,
  },
  prediction: {
    match_id: "event-1",
    home_win_probability: 0.5,
    draw_probability: 0.25,
    away_win_probability: 0.25,
    over_25_probability: 0.6,
    under_25_probability: 0.4,
    predicted_home_goals: 2,
    predicted_away_goals: 1,
    confidence: 0.8,
    data_sources: ["ESPN"],
    recommended_bet: "N/A",
    over_under_recommendation: "N/A",
    created_at: "2026-08-05T00:00:00.000Z",
  },
});

describe("toLiveMatch adapter", () => {
  it("parses '45:00' minute format into a number", () => {
    expect(toLiveMatch(makeEspnMatch()).minute).toBe(45);
  });

  it("parses '45'' minute format into a number", () => {
    expect(toLiveMatch(makeEspnMatch({ minute: "45'" })).minute).toBe(45);
  });

  it("defaults a missing minute to 0", () => {
    expect(toLiveMatch(makeEspnMatch({ minute: undefined })).minute).toBe(0);
  });

  it("preserves HT status and maps every other state to LIVE", () => {
    expect(toLiveMatch(makeEspnMatch({ status: "HT" })).status).toBe("HT");
    expect(toLiveMatch(makeEspnMatch({ status: "LIVE" })).status).toBe("LIVE");
    expect(toLiveMatch(makeEspnMatch({ status: "BREAK" })).status).toBe("LIVE");
  });

  it("flattens the league into league_id/league_name", () => {
    const flat = toLiveMatch(makeEspnMatch());
    expect(flat.league_id).toBe("eng.1");
    expect(flat.league_name).toBe("Premier League");
  });

  it("passes team objects through unchanged", () => {
    const flat = toLiveMatch(makeEspnMatch());
    expect(flat.home_team).toEqual({
      id: "1",
      name: "Home FC",
      logo_url: "h.png",
    });
    expect(flat.away_team).toEqual({
      id: "2",
      name: "Away FC",
      logo_url: "a.png",
    });
  });

  it("keeps score, corners and cards numeric", () => {
    const flat = toLiveMatch(makeEspnMatch());
    expect(flat.home_score).toBe(2);
    expect(flat.away_score).toBe(1);
    expect(flat.home_corners).toBe(4);
    expect(flat.away_corners).toBe(3);
    expect(flat.home_yellow_cards).toBe(1);
    expect(flat.away_yellow_cards).toBe(2);
    expect(flat.home_red_cards).toBe(0);
    expect(flat.away_red_cards).toBe(1);
  });

  it("carries the prediction payload through", () => {
    expect(toLiveMatch(makeEspnMatch()).prediction?.match_id).toBe("event-1");
  });
});

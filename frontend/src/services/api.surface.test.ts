import { describe, expect, it } from "vitest";

import api, { api as namedApi } from "./api";
import apiSource from "./api.ts?raw";

const ENDPOINT_METHODS = [
  "healthCheck",
  "getLeagues",
  "getLeague",
  "getPredictions",
  "getMatchDetails",
  "getLiveMatches",
  "getLiveMatchesWithPredictions",
  "getDailyMatches",
  "getTeamMatches",
  "getSuggestedPicks",
  "registerFeedback",
  "getLearningStats",
];

describe("services/api export surface", () => {
  it("exposes 12 endpoint methods plus generic post/get (14 exports)", () => {
    const exported = Object.keys(api).sort();
    expect(exported).toEqual([...ENDPOINT_METHODS, "get", "post"].sort());
  });

  it("keeps the named `api` and default export in sync", () => {
    expect(api).toBe(namedApi);
  });

  it("contains zero hardcoded /api/v1 literals", () => {
    expect(apiSource).not.toContain("/api/v1");
  });

  it("does not create its own axios instance", () => {
    expect(apiSource).not.toContain("axios.create");
  });

  it("has no references to the deleted parleys/analytics modules", () => {
    expect(apiSource).not.toMatch(
      /parleysApi|analyticsApi|TOP_ML_PICKS|PARLEYS/i
    );
  });
});

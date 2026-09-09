/* eslint-disable import/order */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { leaguesApi } from "./leagues";

import { apiClient } from "./client";

vi.mock("./client", () => ({
  apiClient: {
    get: vi.fn(),
  },
}));
/* eslint-enable import/order */

const mockedGet = vi.mocked(apiClient.get);

describe("leaguesApi sport param", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockedGet.mockResolvedValue({ data: { countries: [], total_leagues: 0 } });
  });

  it("appends ?sport= when getActiveLeagues receives a sport", async () => {
    await leaguesApi.getActiveLeagues("tennis");
    expect(mockedGet).toHaveBeenCalledWith("/api/v1/leagues/active?sport=tennis");
  });

  it("omits sport param when getActiveLeagues is called without sport", async () => {
    await leaguesApi.getActiveLeagues();
    expect(mockedGet).toHaveBeenCalledWith("/api/v1/leagues/active");
  });

  it("appends ?sport= when getLeagues receives a sport", async () => {
    await leaguesApi.getLeagues("baseball");
    expect(mockedGet).toHaveBeenCalledWith("/api/v1/leagues?sport=baseball");
  });

  it("omits param when getLeagues called without sport", async () => {
    await leaguesApi.getLeagues();
    expect(mockedGet).toHaveBeenCalledWith("/api/v1/leagues");
  });

  it("appends ?sport= to getLeague by id", async () => {
    await leaguesApi.getLeague("B_MLB", "baseball");
    expect(mockedGet).toHaveBeenCalledWith("/api/v1/leagues/B_MLB?sport=baseball");
  });

  it("omits sport param from getLeague by id when not provided", async () => {
    await leaguesApi.getLeague("E0");
    expect(mockedGet).toHaveBeenCalledWith("/api/v1/leagues/E0");
  });
});

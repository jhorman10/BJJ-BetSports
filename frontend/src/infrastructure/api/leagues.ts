import { apiClient } from "./client";
import { LeaguesResponse, League } from "../../domain/entities";
import { API_ENDPOINTS } from "../../config/constants";

export const leaguesApi = {
  /**
   * Get all available leagues grouped by country
   */
  async getLeagues(): Promise<LeaguesResponse> {
    const response = await apiClient.get<LeaguesResponse>(
      API_ENDPOINTS.LEAGUES
    );
    return response.data;
  },

  /**
   * Get a specific league by ID
   */
  async getLeague(leagueId: string): Promise<League> {
    const response = await apiClient.get<League>(
      API_ENDPOINTS.LEAGUE_BY_ID(leagueId)
    );
    return response.data;
  },
};

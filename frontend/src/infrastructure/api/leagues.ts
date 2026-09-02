import { LeaguesResponse, League } from "../../domain/entities";
import { API_ENDPOINTS } from "../../config/constants";

import { apiClient } from "./client";

export const leaguesApi = {
  /**
   * Get all available leagues grouped by country
   */
  async getLeagues(sport?: string): Promise<LeaguesResponse> {
    const url = sport
      ? `${API_ENDPOINTS.LEAGUES}?sport=${encodeURIComponent(sport)}`
      : API_ENDPOINTS.LEAGUES;
    const response = await apiClient.get<LeaguesResponse>(url);
    return response.data;
  },

  /**
   * Get only leagues that have active predictions in the database
   */
  async getActiveLeagues(sport?: string): Promise<LeaguesResponse> {
    const url = sport
      ? `${API_ENDPOINTS.LEAGUES_ACTIVE}?sport=${encodeURIComponent(sport)}`
      : API_ENDPOINTS.LEAGUES_ACTIVE;
    const response = await apiClient.get<LeaguesResponse>(url);
    return response.data;
  },

  /**
   * Get a specific league by ID
   */
  async getLeague(leagueId: string, sport?: string): Promise<League> {
    const url = sport
      ? `${API_ENDPOINTS.LEAGUE_BY_ID(leagueId)}?sport=${encodeURIComponent(sport)}`
      : API_ENDPOINTS.LEAGUE_BY_ID(leagueId);
    const response = await apiClient.get<League>(url);
    return response.data;
  },
};

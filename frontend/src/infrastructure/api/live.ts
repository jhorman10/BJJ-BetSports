import { apiClient } from "./client";
import {
  LiveMatchPrediction,
  MatchPrediction,
  Match,
} from "../../domain/entities";
import { fetchESPNLiveMatches } from "../external/espn";
import { API_ENDPOINTS, APP_CONFIG } from "../../config/constants";

export const liveApi = {
  /**
   * Get all live matches globally
   */
  async getLiveMatches(): Promise<Match[]> {
    const response = await apiClient.get<Match[]>(API_ENDPOINTS.MATCHES_LIVE);
    return response.data;
  },

  /**
   * Get live matches with AI predictions
   * Uses backend first, falls back to ESPN if backend empty/fails
   */
  async getLiveMatchesWithPredictions(
    filterTargetLeagues: boolean = true
  ): Promise<LiveMatchPrediction[]> {
    try {
      const response = await apiClient.get<MatchPrediction[]>(
        API_ENDPOINTS.MATCHES_LIVE_WITH_PREDICTIONS,
        {
          params: { filter_target_leagues: filterTargetLeagues },
          timeout: APP_CONFIG.API_TIMEOUT,
        }
      );

      let matches = response.data.map((mp) => ({
        ...mp,
        isProcessing: false,
      })) as LiveMatchPrediction[];

      if (matches.length === 0) {
        matches = await fetchESPNLiveMatches();
      }

      return matches;
    } catch (error) {
      console.error(
        "Backend live matches failed. Falling back to ESPN...",
        error
      );
      return await fetchESPNLiveMatches();
    }
  },
};

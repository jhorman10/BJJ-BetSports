import { apiClient } from "./client";
import { Match } from "../../domain/entities";
import { API_ENDPOINTS } from "../../config/constants";

export const matchesApi = {
  /**
   * Get all matches for today globally
   */
  async getDailyMatches(): Promise<Match[]> {
    const response = await apiClient.get<Match[]>(API_ENDPOINTS.MATCHES_DAILY);
    return response.data;
  },
};

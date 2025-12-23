import { apiClient } from "./client";
import { Parley, GetParleysParams } from "../../domain/entities/parley";
import { API_ENDPOINTS } from "../../config/constants";

export const parleysApi = {
  /**
   * Get AI-suggested parleys (accumulators) based on predictions
   *
   * @param params - Optional parameters to customize parley generation
   * @returns List of AI-generated parley suggestions
   */
  async getSuggestedParleys(params?: GetParleysParams): Promise<Parley[]> {
    const response = await apiClient.get<Parley[]>(API_ENDPOINTS.PARLEYS, {
      params: {
        min_probability: params?.min_probability ?? 0.6,
        min_picks: params?.min_picks ?? 3,
        max_picks: params?.max_picks ?? 5,
        count: params?.count ?? 3,
      },
    });
    return response.data;
  },
};

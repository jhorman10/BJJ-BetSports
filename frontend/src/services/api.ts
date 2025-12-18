/**
 * API Service
 *
 * Handles all HTTP communication with the backend API.
 */

import axios, { AxiosInstance } from "axios";
import {
  LeaguesResponse,
  PredictionsResponse,
  HealthResponse,
  League,
} from "../types";

// API base URL from environment or default
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Create configured Axios instance
 */
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: {
      "Content-Type": "application/json",
    },
  });

  // Response interceptor for error handling
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      console.error("API Error:", error.response?.data || error.message);
      throw error;
    }
  );

  return client;
};

const apiClient = createApiClient();

/**
 * API Service object with all endpoints
 */
export const api = {
  /**
   * Health check
   */
  async healthCheck(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>("/health");
    return response.data;
  },

  /**
   * Get all available leagues grouped by country
   */
  async getLeagues(): Promise<LeaguesResponse> {
    const response = await apiClient.get<LeaguesResponse>("/api/v1/leagues");
    return response.data;
  },

  /**
   * Get a specific league by ID
   */
  async getLeague(leagueId: string): Promise<League> {
    const response = await apiClient.get<League>(`/api/v1/leagues/${leagueId}`);
    return response.data;
  },

  /**
   * Get predictions for a league
   */
  async getPredictions(
    leagueId: string,
    limit: number = 10
  ): Promise<PredictionsResponse> {
    const response = await apiClient.get<PredictionsResponse>(
      `/api/v1/predictions/league/${leagueId}`,
      { params: { limit } }
    );
    return response.data;
  },
};

export default api;

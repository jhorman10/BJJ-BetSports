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
  MatchPrediction,
  Match,
  LiveMatchPrediction,
  MatchSuggestedPicks,
  BettingFeedbackRequest,
  BettingFeedbackResponse,
  LearningStatsResponse,
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
      // Don't log 404s as errors globally - they are often expected "no data" states
      if (error.response && error.response.status !== 404) {
        console.error("API Error:", error.response?.data || error.message);
      }
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
   * Get predictions for a league with optional sorting
   */
  async getPredictions(
    leagueId: string,
    limit: number = 30,
    sortBy:
      | "date"
      | "confidence"
      | "home_probability"
      | "away_probability" = "confidence",
    sortDesc: boolean = true
  ): Promise<PredictionsResponse> {
    const response = await apiClient.get<PredictionsResponse>(
      `/api/v1/predictions/league/${leagueId}`,
      { params: { limit, sort_by: sortBy, sort_desc: sortDesc } }
    );
    return response.data;
  },

  /**
   * Get prediction/details for a specific match
   */
  async getMatchDetails(matchId: string): Promise<MatchPrediction> {
    const response = await apiClient.get<MatchPrediction>(
      `/api/v1/predictions/match/${matchId}`
    );
    return response.data;
  },

  /**
   * Get all live matches globally
   */
  async getLiveMatches(): Promise<Match[]> {
    const response = await apiClient.get<Match[]>("/api/v1/matches/live");
    return response.data;
  },

  /**
   * Get live matches with AI predictions
   * Optimized for accuracy - uses caching for fast subsequent loads
   */
  async getLiveMatchesWithPredictions(
    filterTargetLeagues: boolean = true
  ): Promise<LiveMatchPrediction[]> {
    const response = await apiClient.get<MatchPrediction[]>(
      "/api/v1/matches/live/with-predictions",
      {
        params: { filter_target_leagues: filterTargetLeagues },
        timeout: 10000, // 10s timeout for this endpoint
      }
    );
    return response.data;
  },

  /**
   * Get all matches for today globally
   */
  async getDailyMatches(): Promise<Match[]> {
    const response = await apiClient.get<Match[]>("/api/v1/matches/daily");
    return response.data;
  },

  /**
   * Get matches for a specific team
   */
  async getTeamMatches(teamName: string): Promise<Match[]> {
    const response = await apiClient.get<Match[]>(
      `/api/v1/matches/team/${teamName}`
    );
    return response.data;
  },

  /**
   * Get AI-suggested picks for a match
   */
  async getSuggestedPicks(matchId: string): Promise<MatchSuggestedPicks> {
    const response = await apiClient.get<MatchSuggestedPicks>(
      `/api/v1/suggested-picks/match/${matchId}`
    );
    return response.data;
  },

  /**
   * Register betting feedback for continuous learning
   */
  async registerFeedback(
    feedback: BettingFeedbackRequest
  ): Promise<BettingFeedbackResponse> {
    const response = await apiClient.post<BettingFeedbackResponse>(
      `/api/v1/suggested-picks/feedback`,
      feedback
    );
    return response.data;
  },

  /**
   * Get learning statistics from feedback
   */
  async getLearningStats(): Promise<LearningStatsResponse> {
    const response = await apiClient.get<LearningStatsResponse>(
      `/api/v1/suggested-picks/learning-stats`
    );
    return response.data;
  },

  /**
   * Generic POST method for flexibility
   * Automatically increases timeout for /train endpoint (5 minutes)
   */
  async post<T>(endpoint: string, data?: any): Promise<T> {
    // Use extended timeout for training endpoint (only runs once per day)
    const config = endpoint === "/train" ? { timeout: 300000 } : {}; // 5 minutes for /train
    const response = await apiClient.post<T>(
      `/api/v1${endpoint}`,
      data,
      config
    );
    return response.data;
  },
};

export default api;

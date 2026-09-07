/**
 * API Service
 *
 * Handles all HTTP communication with the backend API.
 * Transport is the single canonical client from infrastructure/api/client.ts;
 * endpoint paths come exclusively from API_ENDPOINTS (config/constants.ts).
 */

import { apiClient } from "../infrastructure/api/client";
import { API_ENDPOINTS, APP_CONFIG } from "../config/constants";
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
  TennisMatchRequest,
  TennisPredictionResponse,
  TennisUpcomingResponse,
  TennisTournamentsResponse,
  TennisPredictionsResponse,
  BaseballPredictRequest,
  BaseballPredictResponse,
  BaseballGamesResponse,
  BaseballSeriesResponse,
  BasketballPredictRequest,
  BasketballPredictResponse,
  BasketballGamesResponse,
  BasketballConferencesResponse,
  BasketballConferenceGamesResponse,
} from "../types";

/**
 * API Service object with all endpoints
 */
export const api = {
  /**
   * Health check
   */
  async healthCheck(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>(API_ENDPOINTS.HEALTH);
    return response.data;
  },

  /**
   * Get all available leagues grouped by country
   */
  async getLeagues(): Promise<LeaguesResponse> {
    const response = await apiClient.get<LeaguesResponse>(API_ENDPOINTS.LEAGUES);
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

  /**
   * Get predictions for a league with optional sorting
   */
  async getPredictions(
    leagueId: string,
    limit: number = APP_CONFIG.DEFAULT_PREDICTIONS_LIMIT,
    sortBy:
      | "date"
      | "confidence"
      | "home_probability"
      | "away_probability" = "confidence",
    sortDesc: boolean = true
  ): Promise<PredictionsResponse> {
    const response = await apiClient.get<PredictionsResponse>(
      API_ENDPOINTS.PREDICTIONS_BY_LEAGUE(leagueId),
      { params: { limit, sort_by: sortBy, sort_desc: sortDesc } }
    );
    return response.data;
  },

  /**
   * Get prediction/details for a specific match
   */
  async getMatchDetails(matchId: string): Promise<MatchPrediction> {
    const response = await apiClient.get<MatchPrediction>(
      API_ENDPOINTS.PREDICTION_BY_MATCH(matchId)
    );
    return response.data;
  },

  /**
   * Get all live matches globally
   */
  async getLiveMatches(): Promise<Match[]> {
    const response = await apiClient.get<Match[]>(API_ENDPOINTS.MATCHES_LIVE);
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
      API_ENDPOINTS.MATCHES_LIVE_WITH_PREDICTIONS,
      {
        params: { filter_target_leagues: filterTargetLeagues },
        timeout: APP_CONFIG.LIVE_API_TIMEOUT, // 30s timeout for live matches
      }
    );
    return response.data;
  },

  /**
   * Get all matches for today globally
   */
  async getDailyMatches(): Promise<Match[]> {
    const response = await apiClient.get<Match[]>(API_ENDPOINTS.MATCHES_DAILY);
    return response.data;
  },

  /**
   * Get matches for a specific team
   */
  async getTeamMatches(teamName: string): Promise<Match[]> {
    const response = await apiClient.get<Match[]>(
      API_ENDPOINTS.MATCHES_BY_TEAM(teamName)
    );
    return response.data;
  },

  /**
   * Get AI-suggested picks for a match
   */
  async getSuggestedPicks(matchId: string): Promise<MatchSuggestedPicks> {
    const response = await apiClient.get<MatchSuggestedPicks>(
      API_ENDPOINTS.SUGGESTED_PICKS_BY_MATCH(matchId),
      {
        timeout: APP_CONFIG.SUGGESTED_PICKS_TIMEOUT, // 90s for slow pick generation
      }
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
      API_ENDPOINTS.SUGGESTED_PICKS_FEEDBACK,
      feedback
    );
    return response.data;
  },

  /**
   * Tennis match prediction
   */
  async predictTennis(data: TennisMatchRequest): Promise<TennisPredictionResponse> {
    const response = await apiClient.post<TennisPredictionResponse>(
      API_ENDPOINTS.TENNIS_PREDICT,
      data
    );
    return response.data;
  },

  /**
   * Get upcoming tennis matches with predictions
   */
  async getTennisUpcoming(): Promise<TennisUpcomingResponse> {
    const response = await apiClient.get<TennisUpcomingResponse>(
      API_ENDPOINTS.TENNIS_UPCOMING
    );
    return response.data;
  },

  /**
   * Get available tennis tournaments
   */
  async getTennisTournaments(): Promise<TennisTournamentsResponse> {
    const response = await apiClient.get<TennisTournamentsResponse>(
      API_ENDPOINTS.TENNIS_TOURNAMENTS
    );
    return response.data;
  },

  /**
   * Get predictions for a specific tennis tournament
   */
  async getTennisPredictionsByTournament(
    tournamentId: string
  ): Promise<TennisPredictionsResponse> {
    const response = await apiClient.get<TennisPredictionsResponse>(
      API_ENDPOINTS.TENNIS_PREDICT_BY_TOURNAMENT(tournamentId)
    );
    return response.data;
  },

  /**
   * Baseball game prediction
   */
  async predictBaseball(data: BaseballPredictRequest): Promise<BaseballPredictResponse> {
    const response = await apiClient.post<BaseballPredictResponse>(
      API_ENDPOINTS.BASEBALL_PREDICT,
      data
    );
    return response.data;
  },

  /**
   * Get upcoming baseball games
   */
  async getBaseballGames(team?: string): Promise<BaseballGamesResponse> {
    const response = await apiClient.get<BaseballGamesResponse>(
      API_ENDPOINTS.BASEBALL_GAMES,
      { params: team ? { team } : {} }
    );
    return response.data;
  },

  /**
   * Get upcoming baseball series with predictions
   */
  async getBaseballSeries(team?: string): Promise<BaseballSeriesResponse> {
    const response = await apiClient.get<BaseballSeriesResponse>(
      API_ENDPOINTS.BASEBALL_SERIES,
      { params: team ? { team } : {} }
    );
    return response.data;
  },

  /**
   * Get predictions for a specific baseball series
   */
  async getBaseballSeriesPredictions(
    seriesId: string
  ): Promise<{ series_id: string; games: unknown[]; generated_at: string }> {
    const response = await apiClient.get(
      API_ENDPOINTS.BASEBALL_SERIES_PREDICTIONS(seriesId)
    );
    return response.data;
  },

  /**
   * Basketball game prediction
   */
  async predictBasketball(data: BasketballPredictRequest): Promise<BasketballPredictResponse> {
    const response = await apiClient.post<BasketballPredictResponse>(
      API_ENDPOINTS.BASKETBALL_PREDICT,
      data
    );
    return response.data;
  },

  /**
   * Get upcoming basketball games
   */
  async getBasketballGames(team?: string): Promise<BasketballGamesResponse> {
    const response = await apiClient.get<BasketballGamesResponse>(
      API_ENDPOINTS.BASKETBALL_GAMES,
      { params: team ? { team } : {} }
    );
    return response.data;
  },

  /**
   * Get available basketball conferences
   */
  async getBasketballConferences(): Promise<BasketballConferencesResponse> {
    const response = await apiClient.get<BasketballConferencesResponse>(
      API_ENDPOINTS.BASKETBALL_CONFERENCES
    );
    return response.data;
  },

  /**
   * Get predictions for a specific conference
   */
  async getBasketballPredictionsByConference(
    conferenceId: string
  ): Promise<BasketballConferenceGamesResponse> {
    const response = await apiClient.get<BasketballConferenceGamesResponse>(
      API_ENDPOINTS.BASKETBALL_PREDICT_BY_CONFERENCE(conferenceId)
    );
    return response.data;
  },

  /**
   * Get learning statistics from feedback
   */
  async getLearningStats(): Promise<LearningStatsResponse> {
    const response = await apiClient.get<LearningStatsResponse>(
      API_ENDPOINTS.LEARNING_STATS
    );
    return response.data;
  },

  /**
   * Generic POST method for flexibility
   */
  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    const response = await apiClient.post<T>(
      `${API_ENDPOINTS.API_V1_PREFIX}${endpoint}`,
      data
    );
    return response.data;
  },

  /**
   * Generic GET method for flexibility
   */
  async get<T>(endpoint: string): Promise<T> {
    const response = await apiClient.get<T>(
      `${API_ENDPOINTS.API_V1_PREFIX}${endpoint}`
    );
    return response.data;
  },
};

export default api;

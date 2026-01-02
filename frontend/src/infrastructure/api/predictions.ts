import { apiClient } from "./client";
import {
  PredictionsResponse,
  MatchPrediction,
  MatchSuggestedPicks,
  BettingFeedbackRequest,
  BettingFeedbackResponse,
  LearningStatsResponse,
} from "../../domain/entities";
import { API_ENDPOINTS, APP_CONFIG } from "../../config/constants";

export const predictionsApi = {
  /**
   * Get predictions for a league with optional sorting
   */
  async getPredictions(
    leagueId: string,
    limit: number = 10,
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
   * Get AI-suggested picks for a match
   */
  async getSuggestedPicks(matchId: string): Promise<MatchSuggestedPicks> {
    const response = await apiClient.get<MatchSuggestedPicks>(
      API_ENDPOINTS.SUGGESTED_PICKS_BY_MATCH(matchId)
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
   * Get learning statistics from feedback
   */
  async getLearningStats(): Promise<LearningStatsResponse> {
    const response = await apiClient.get<LearningStatsResponse>(
      API_ENDPOINTS.LEARNING_STATS
    );
    return response.data;
  },

  /**
   * Generic Post used for Training
   */
  async train(data: any): Promise<any> {
    const response = await apiClient.post(API_ENDPOINTS.TRAIN, data, {
      timeout: APP_CONFIG.TRAINING_TIMEOUT,
    });
    return response.data;
  },

  /**
   * Get matches for a specific team
   */
  async getTeamMatches(teamName: string): Promise<MatchPrediction[]> {
    const response = await apiClient.get<MatchPrediction[]>(
      API_ENDPOINTS.MATCHES_BY_TEAM(teamName)
    );
    return response.data;
  },

  /**
   * Get current training status
   */
  async getTrainingStatus(): Promise<{
    status: string;
    message: string;
    last_update?: string;
    has_result: boolean;
  }> {
    const response = await apiClient.get(API_ENDPOINTS.TRAINING_STATUS);
    return response.data;
  },
};

/**
 * TypeScript interfaces for the Football Prediction API
 */

export interface Team {
  id: string;
  name: string;
  short_name?: string;
  country?: string;
  logo_url?: string;
}

export interface League {
  id: string;
  name: string;
  country: string;
  season?: string;
}

export interface Match {
  id: string;
  home_team: Team;
  away_team: Team;
  league: League;
  match_date: string;
  home_goals?: number;
  away_goals?: number;
  status: string;
  home_corners?: number;
  away_corners?: number;
  home_yellow_cards?: number;
  away_yellow_cards?: number;
  home_red_cards?: number;
  away_red_cards?: number;
  home_odds?: number;
  draw_odds?: number;
  away_odds?: number;
}

export interface Prediction {
  match_id: string;
  home_win_probability: number;
  draw_probability: number;
  away_win_probability: number;
  over_25_probability: number;
  under_25_probability: number;
  predicted_home_goals: number;
  predicted_away_goals: number;

  // New Standard Probabilities
  over_95_corners_probability?: number;
  under_95_corners_probability?: number;
  over_45_cards_probability?: number;
  under_45_cards_probability?: number;

  // Dynamic Handicap
  handicap_line?: number;
  handicap_home_probability?: number;
  handicap_away_probability?: number;

  // Value Bet
  expected_value?: number;
  is_value_bet?: boolean;

  confidence: number;
  data_sources: string[];
  recommended_bet: string;
  over_under_recommendation: string;
  created_at: string;
  data_updated_at?: string;
  fundamental_analysis?: Record<string, boolean>;
}

export interface MatchPrediction {
  match: Match;
  prediction: Prediction;
}

export interface Country {
  name: string;
  code: string;
  flag?: string;
  leagues: League[];
}

export interface LeaguesResponse {
  countries: Country[];
  total_leagues: number;
}

export interface PredictionsResponse {
  league: League;
  predictions: MatchPrediction[];
  generated_at: string;
}

export interface HealthResponse {
  status: string;
  version: string;
  timestamp: string;
}

export interface ApiError {
  error: string;
  message: string;
  details?: Record<string, unknown>;
}

/**
 * Live match with prediction data
 */
export interface LiveMatchPrediction extends MatchPrediction {
  isProcessing?: boolean;
  processingMessage?: string;
}

/**
 * Response for live matches with predictions endpoint
 */
export interface LiveMatchesResponse {
  matches: LiveMatchPrediction[];
  processingMessage: string;
  lastUpdated: string;
}

/**
 * Suggested betting pick from AI
 */
export interface SuggestedPick {
  market_type: string;
  market_label: string;
  probability: number;
  confidence_level: "high" | "medium" | "low";
  reasoning: string;
  risk_level: number;
  is_recommended: boolean;
  priority_score: number;
}

/**
 * Container for all suggested picks for a match
 */
export interface MatchSuggestedPicks {
  match_id: string;
  suggested_picks: SuggestedPick[];
  combination_warning?: string;
  generated_at: string;
}

/**
 * Request for registering betting feedback
 */
export interface BettingFeedbackRequest {
  match_id: string;
  market_type: string;
  prediction: string;
  actual_outcome: string;
  was_correct: boolean;
  odds: number;
  stake?: number;
}

/**
 * Response for betting feedback registration
 */
export interface BettingFeedbackResponse {
  success: boolean;
  message: string;
  market_type: string;
  new_confidence_adjustment: number;
}

/**
 * Market performance statistics
 */
export interface MarketPerformance {
  market_type: string;
  total_predictions: number;
  correct_predictions: number;
  success_rate: number;
  avg_odds: number;
  total_profit_loss: number;
  confidence_adjustment: number;
  last_updated: string;
}

/**
 * Learning statistics response
 */
export interface LearningStatsResponse {
  market_performances: MarketPerformance[];
  total_feedback_count: number;
  last_updated: string;
}

// Export all component props and types
export * from "./components";

/**
 * TypeScript interfaces for the Football Prediction API
 */

export * from "./training";

export interface Team {
  id: string;
  name: string;
  short_name?: string;
  country?: string;
  logo_url?: string;
}

export type Sport = "soccer" | "tennis" | "baseball" | "basketball";

export interface League {
  id: string;
  name: string;
  country: string;
  season?: string;
  flag?: string;
  sport?: Sport;
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
  home_possession?: string;
  away_possession?: string;
  home_total_shots?: number;
  away_total_shots?: number;
  home_shots_on_target?: number;
  away_shots_on_target?: number;
  home_fouls?: number;
  away_fouls?: number;
  home_offsides?: number;
  away_offsides?: number;
  home_spi?: number;
  away_spi?: number;
}

export interface Prediction {
  id?: string;
  match_id: string;
  home_win_probability: number;
  draw_probability: number;
  away_win_probability: number;
  over_25_probability: number;
  under_25_probability: number;
  predicted_home_goals: number;
  predicted_away_goals: number;

  predicted_home_corners?: number;
  predicted_away_corners?: number;
  predicted_home_yellow_cards?: number;
  predicted_away_yellow_cards?: number;
  predicted_home_red_cards?: number;
  predicted_away_red_cards?: number;

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
  suggested_picks?: import("./index").SuggestedPick[];
  highlights_url?: string;
  real_time_odds?: Record<string, number>;
  data_updated_at?: string;
  fundamental_analysis?: Record<string, boolean>;

  // Marcador Tentativo
  score_probabilities?: ScoreProbability[];
  score_confidence_tier?: "Alta" | "Media" | "Baja" | "N/A";
  score_matrix?: ScoreCell[][];
  score_accuracy_history?: ScoreAccuracyHistory;
}

export interface ScoreProbability {
  home_goals: number;
  away_goals: number;
  probability: number;
}

export interface ScoreCell {
  home_goals: number;
  away_goals: number;
  probability: number;
  home_xg_contribution: number;
  away_xg_contribution: number;
}

export interface ScoreAccuracyHistory {
  league_id: string;
  total_predictions: number;
  exact_score_hits: number;
  accuracy_percentage: number;
}

export interface MatchPrediction {
  match: Match;
  prediction: Prediction;
  top_ml_picks?: import("./index").SuggestedPick[];
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
  // Historical/result properties
  was_correct?: boolean;
  expected_value?: number;
  confidence?: number;
  is_contrarian?: boolean;
  pick_code?: string; // Short code like '1', 'X', '2', 'O2.5'

  // Risk & Professional fields
  suggested_stake?: number;
  kelly_percentage?: number;
  opening_odds?: number;
  closing_odds?: number;
  clv_beat?: boolean;
  is_ml_confirmed?: boolean;
  is_ia_confirmed?: boolean; // [NEW] Unique flag for the absolute best pick
  formatted_reasoning?: string; // [NEW] Structured reasoning for UI
  ml_confidence?: number;

  // SSOT fields from Backend (Auditoría v4)
  color_code?: string; // Hex color from backend
  result?: string; // WIN, LOSS, VOID, PENDING
}

/**
 * Container for all suggested picks for a match
 */
export interface MatchSuggestedPicks {
  match_id: string;
  suggested_picks: SuggestedPick[];
  combination_warning?: string;
  highlights_url?: string;
  real_time_odds?: Record<string, number>;
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

/**
 * Tennis Prediction Types
 */
export interface TennisMatchRequest {
  tournament_name: string;
  surface: string;
  tourney_level: string;
  round_name: string;
  match_date: string;
  best_of: number;
  p1_name: string;
  p1_rank?: number;
  p1_rank_points?: number;
  p1_age?: number;
  p1_hand?: string;
  p1_height?: number;
  p1_seed?: number;
  p1_entry?: string;
  p1_odds?: number;
  p2_name: string;
  p2_rank?: number;
  p2_rank_points?: number;
  p2_age?: number;
  p2_hand?: string;
  p2_height?: number;
  p2_seed?: number;
  p2_entry?: string;
  p2_odds?: number;
}

export interface TennisPredictionResponse {
  match_id: string;
  p1_name: string;
  p2_name: string;
  p1_win_prob: number;
  p2_win_prob: number;
  predicted_winner: string;
  confidence: number;
  surface: string;
  tournament_name: string;
}

export interface TennisUpcomingPlayer {
  name: string;
  rank: number | null;
  rank_points?: number | null;
  age?: number | null;
  hand?: string;
  height?: number | null;
  seed: number | null;
}

export interface TennisUpcomingPrediction {
  p1_win_prob: number;
  p2_win_prob: number;
  predicted_winner: string;
  confidence: number;
  h2h: {
    total_matches: number;
    p1_wins: number;
    p2_wins: number;
  };
  surface_stats: {
    p1_surface_win_rate: number;
    p2_surface_win_rate: number;
    surface: string;
  };
  form: {
    p1_win_rate_5: number;
    p2_win_rate_5: number;
    p1_win_rate_10: number;
    p2_win_rate_10: number;
    p1_ace_rate: number;
    p2_ace_rate: number;
    p1_first_serve_pct: number;
    p2_first_serve_pct: number;
  };
  value_bets: Array<{
    player: string;
    odds: number;
    implied_prob: number;
    model_prob: number;
    edge: number;
    type: string;
  }>;
  key_factors: string[];
  markets: TennisMarket[];
}

export interface TennisMarket {
  market_type: string;
  market_label: string;
  probability: number;
  confidence_level: "high" | "medium" | "low";
  reasoning: string;
  risk_level: number;
  is_recommended: boolean;
  priority_score: number;
  pick_code: string;
}

export interface TennisUpcomingMatch {
  match_id: string;
  tournament: string;
  surface: string;
  round: string;
  match_date: string;
  best_of?: number;
  player1: TennisUpcomingPlayer;
  player2: TennisUpcomingPlayer;
  prediction: TennisUpcomingPrediction;
}

export interface TennisUpcomingResponse {
  matches: TennisUpcomingMatch[];
}

export interface TennisTournament {
  id: string;
  name: string;
  surface: string;
  level: string;
  match_count: number;
}

export interface TennisTournamentsResponse {
  tournaments: TennisTournament[];
  total_matches: number;
}

export interface TennisPredictionsResponse {
  tournament: TennisTournament | null;
  matches: TennisUpcomingMatch[];
  generated_at: string | null;
}

// Baseball Prediction Types
export * from "./baseball";

// Basketball Prediction Types
export * from "./basketball";

// Best Combination Types
export * from "./bestCombination";

// Export all component props and types
export * from "./components";

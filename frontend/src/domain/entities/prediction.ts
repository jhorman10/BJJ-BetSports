import { Match, League } from "./match";
import { SuggestedPick } from "./pick";

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
  data_updated_at?: string;
  highlights_url?: string;
  real_time_odds?: Record<string, number>;
  fundamental_analysis?: Record<string, boolean>;
  suggested_picks?: SuggestedPick[];

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
  top_ml_picks?: SuggestedPick[];
}

export interface PredictionsResponse {
  league: League;
  predictions: MatchPrediction[];
  generated_at: string;
}

/**
 * Live match with prediction data
 */
export interface LiveMatchPrediction extends MatchPrediction {
  isProcessing?: boolean;
  processingMessage?: string;
}

export interface LiveMatchesResponse {
  matches: LiveMatchPrediction[];
  processingMessage: string;
  lastUpdated: string;
}

import { Match, League } from "./match";

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
  suggested_picks?: SuggestedPick[];
}

export interface SuggestedPick {
  market_type: string;
  market_label: string;
  probability: number;
  confidence_level: "high" | "medium" | "low";
  reasoning: string;
  risk_level: number;
  is_recommended: boolean;
  priority_score: number;
  was_correct?: boolean;
  expected_value?: number;
  confidence?: number;
  suggested_stake?: number;
  kelly_percentage?: number;
  opening_odds?: number;
  closing_odds?: number;
  clv_beat?: boolean;
  odds?: number;
}

export interface MatchPrediction {
  match: Match;
  prediction: Prediction;
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

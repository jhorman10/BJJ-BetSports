/**
 * Basketball Prediction Types
 */

export interface BasketballGame {
  game_id: string;
  date: string;
  home_team: string;
  away_team: string;
  venue?: string;
  home_team_name?: string;
  away_team_name?: string;
  home_odds?: number;
  away_odds?: number;
}

export interface BasketballMarket {
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

export interface BasketballPrediction {
  home_win_prob: number;
  away_win_prob: number;
  predicted_winner: string;
  confidence: number;
  key_factors: string[];
  markets: BasketballMarket[];
}

export interface BasketballGameWithPrediction extends BasketballGame {
  prediction: BasketballPrediction;
}

export interface BasketballConference {
  id: string;
  name: string;
  teams: string[];
}

export interface BasketballConferencesResponse {
  conferences: BasketballConference[];
  generated_at: string;
}

export interface BasketballConferenceGamesResponse {
  conference_id: string;
  conference_name: string;
  games: BasketballGameWithPrediction[];
  generated_at: string;
}

export interface BasketballGamesResponse {
  games: BasketballGame[];
  generated_at: string;
}

export interface BasketballPredictRequest {
  date: string;
  home_team: string;
  away_team: string;
  venue?: string;
  season?: string;
  game_type?: string;
  home_odds?: number;
  away_odds?: number;
  spread?: number;
  total?: number;
}

export interface BasketballPredictResponse {
  game_id: string;
  home_team: string;
  away_team: string;
  home_win_prob: number;
  away_win_prob: number;
  predicted_winner: string;
  confidence: number;
}

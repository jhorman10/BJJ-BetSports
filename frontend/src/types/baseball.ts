/**
 * Baseball Prediction Types
 */

export interface BaseballGame {
  game_id: string;
  date: string;
  home_team: string;
  away_team: string;
  venue?: string;
  day_night: "day" | "night";
  home_pitcher_name?: string;
  away_pitcher_name?: string;
  home_odds?: number;
  away_odds?: number;
}

export interface BaseballMarket {
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

export interface BaseballPrediction {
  home_win_prob: number;
  away_win_prob: number;
  predicted_winner: string;
  confidence: number;
  key_factors: string[];
  markets: BaseballMarket[];
}

export interface BaseballGameWithPrediction extends BaseballGame {
  prediction: BaseballPrediction;
}

export interface BaseballSeries {
  series_id: string;
  home_team: string;
  away_team: string;
  game_count: number;
  games: BaseballGameWithPrediction[];
}

export interface BaseballGamesResponse {
  games: BaseballGame[];
  generated_at: string;
}

export interface BaseballSeriesResponse {
  series: BaseballSeries[];
  generated_at: string;
  is_demo: boolean;
}

export interface BaseballPredictRequest {
  date: string;
  home_team: string;
  away_team: string;
  venue?: string;
  day_night?: "day" | "night";
  home_pitcher_name?: string;
  away_pitcher_name?: string;
  season?: number;
  series_id?: string;
  home_odds?: number;
  away_odds?: number;
}

export interface BaseballPredictResponse {
  game_id: string;
  home_team: string;
  away_team: string;
  home_win_prob: number;
  away_win_prob: number;
  predicted_winner: string;
  confidence: number;
}

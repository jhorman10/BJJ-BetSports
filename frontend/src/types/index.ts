/**
 * TypeScript interfaces for the Football Prediction API
 */

export interface Team {
  id: string;
  name: string;
  short_name?: string;
  country?: string;
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
  confidence: number;
  data_sources: string[];
  recommended_bet: string;
  over_under_recommendation: string;
  created_at: string;
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

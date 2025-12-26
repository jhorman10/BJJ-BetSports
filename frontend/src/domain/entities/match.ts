export interface Team {
  id: string;
  name: string;
  short_name?: string;
  country?: string;
  logo_url?: string;
  logo?: string; // Add logo property to match usage in App.tsx
}

export interface League {
  id: string;
  name: string;
  country: string;
  season?: string;
  flag?: string;
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
  minute?: string;
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
  events?: MatchEvent[];
}

export interface MatchEvent {
  time: string;
  team_id: string;
  player_name: string;
  type: string;
  detail: string;
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

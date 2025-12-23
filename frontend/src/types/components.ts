/**
 * Component Props Interfaces
 * This file contains all prop interfaces for React components
 */

import {
  MatchPrediction,
  League,
  LiveMatchPrediction,
  SuggestedPick,
} from "./index";

// Multiple picks per match
export interface PickDetail {
  event_type: string; // "Resultado", "Total Goles", etc.
  pick: string; // "1 (Real Madrid)", "Over 2.5", etc.
  was_correct: boolean;
  expected_value: number;
  confidence: number;
}

// BotDashboard related types
export interface MatchPredictionHistory {
  match_id: string;
  home_team: string;
  away_team: string;
  match_date: string;
  predicted_winner: string;
  actual_winner: string;
  predicted_home_goals: number;
  predicted_away_goals: number;
  actual_home_goals: number;
  actual_away_goals: number;
  was_correct: boolean;
  confidence: number;
  picks: SuggestedPick[]; // Multiple picks
  suggested_pick?: string | null; // Legacy
  pick_was_correct?: boolean | null;
  expected_value?: number | null;
}

export interface TrainingStatus {
  matches_processed: number;
  correct_predictions: number;
  accuracy: number;
  total_bets: number;
  roi: number;
  profit_units: number;
  market_stats: any;
  match_history: MatchPredictionHistory[];
}

export interface MatchHistoryTableProps {
  matches: MatchPredictionHistory[];
}

// Parley related types
export interface ParleyPickItem {
  matchId: string;
  matchName: string;
  selectedMarket: string;
  probability: number;
}

export interface ParleySectionProps {
  predictions: MatchPrediction[];
}

export interface ParleySlipProps {
  picks: ParleyPickItem[];
  onRemovePick: (matchId: string) => void;
  onClear: () => void;
}

// MatchCard
export interface MatchCardProps {
  matchPrediction: MatchPrediction;
  onSelectPick?: (pick: ParleyPickItem) => void;
}

// PredictionGrid
export interface PredictionGridProps {
  predictions: MatchPrediction[];
}

export interface PredictionGridListProps {
  predictions: MatchPrediction[];
  onSelectPick?: (pick: ParleyPickItem) => void;
}

export interface PredictionGridHeaderProps {
  selectedLeague: League | null;
  selectedCountry: string | null;
  sortBy: string;
  sortDirection: "asc" | "desc";
  onSortChange: (newSortBy: string) => void;
  onSortDirectionToggle: () => void;
}

// LeagueSelector
export interface LeagueSelectorProps {
  onLeagueChange: (league: League | null) => void;
  onCountryChange: (country: string | null) => void;
}

export interface CountrySelectProps {
  selectedCountry: string | null;
  onCountryChange: (country: string | null) => void;
}

export interface LeagueSelectProps {
  selectedCountry: string | null;
  selectedLeague: League | null;
  onLeagueChange: (league: League | null) => void;
}

// MatchDetails
export interface MatchDetailsModalProps {
  open: boolean;
  onClose: () => void;
  matchPrediction: MatchPrediction | null;
}

export interface SuggestedPicksTabProps {
  matchPrediction: MatchPrediction;
}

// LiveMatches
export interface LiveMatchesListProps {
  matches: LiveMatchPrediction[];
}

export interface LiveMatchesViewProps {
  matches: LiveMatchPrediction[];
  isLoading: boolean;
  error: string | null;
}

export interface LiveMatchCardProps {
  match: LiveMatchPrediction;
}

// TeamSearch
export interface TeamSearchProps {
  onTeamSelect: (teamId: string) => void;
}

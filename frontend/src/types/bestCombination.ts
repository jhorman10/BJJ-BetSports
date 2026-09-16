/**
 * Best Combination Types
 *
 * Mirror of the backend DTOs in
 * `backend/src/api/dtos/best_combination_dtos.py`.
 */

export interface BestCombinationRequest {
  /** Discard candidate legs below this probability (0 < p < 1). */
  min_probability?: number;
  /** League/tournament identifiers to exclude from the combination. */
  exclude_leagues?: string[];
}

export interface BestCombinationLeg {
  sport: string;
  match_id: string;
  match_label: string;
  pick_label: string;
  league: string | null;
  probability: number;
  odds: number;
  odds_source: "market" | "fair";
  confidence_level: string;
  is_recommended: boolean;
  priority_score: number;
  confidence_warning: boolean;
  odds_warning: boolean;
}

export interface BestCombinationAggregate {
  total_probability: number;
  total_odds: number;
  expected_value: number;
  mixed_odds: boolean;
}

export interface BestCombinationStake {
  suggested_stake_pct: number;
  risk_level: number;
  kelly_fraction: number;
}

export interface BestCombinationResponse {
  legs: BestCombinationLeg[];
  aggregate: BestCombinationAggregate;
  stake: BestCombinationStake;
  generated_at: string;
  independence_disclaimer: string;
  warnings: string[];
}
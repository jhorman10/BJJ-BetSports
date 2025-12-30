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
  // Historical/result properties
  was_correct?: boolean;
  expected_value?: number;
  confidence?: number;
  is_contrarian?: boolean;
  pick_code?: string; // Short code like '1', 'X', '2', 'O2.5'

  // Betting Management (Merged from prediction.ts)
  suggested_stake?: number;
  kelly_percentage?: number;
  opening_odds?: number;
  closing_odds?: number;
  clv_beat?: boolean;
  odds?: number;
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

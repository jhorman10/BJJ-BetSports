import { SuggestedPick } from "./pick";

/**
 * Represents a combination of bets (parley/accumulator)
 */
export interface Parley {
  parley_id: string;
  picks: SuggestedPick[];
  total_odds: number;
  total_probability: number;
}

/**
 * Request parameters for fetching AI-suggested parleys
 */
export interface GetParleysParams {
  min_probability?: number; // 0.5 - 1.0, default 0.60
  min_picks?: number; // 2-10, default 3
  max_picks?: number; // 2-10, default 5
  count?: number; // 1-10, default 3
}

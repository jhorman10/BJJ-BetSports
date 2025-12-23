/**
 * Market performance statistics
 */
export interface MarketPerformance {
  market_type: string;
  total_predictions: number;
  correct_predictions: number;
  success_rate: number;
  avg_odds: number;
  total_profit_loss: number;
  confidence_adjustment: number;
  last_updated: string;
}

/**
 * Learning statistics response
 */
export interface LearningStatsResponse {
  market_performances: MarketPerformance[];
  total_feedback_count: number;
  last_updated: string;
}

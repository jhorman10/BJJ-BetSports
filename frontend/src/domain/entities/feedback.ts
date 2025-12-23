/**
 * Request for registering betting feedback
 */
export interface BettingFeedbackRequest {
  match_id: string;
  market_type: string;
  prediction: string;
  actual_outcome: string;
  was_correct: boolean;
  odds: number;
  stake?: number;
}

/**
 * Response for betting feedback registration
 */
export interface BettingFeedbackResponse {
  success: boolean;
  message: string;
  market_type: string;
  new_confidence_adjustment: number;
}

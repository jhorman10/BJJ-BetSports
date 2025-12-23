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

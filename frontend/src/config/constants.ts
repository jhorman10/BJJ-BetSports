/**
 * API Endpoints Constants
 * Centralized endpoint definitions - single source of truth
 */

export const API_ENDPOINTS = {
  // Generic version prefix used by the flexible services layer
  API_V1_PREFIX: "/api/v1",

  // Leagues
  // NOTE: LEAGUES / LEAGUES_ACTIVE support ?sport= query param for filtering.
  LEAGUES: "/api/v1/leagues",
  LEAGUES_ACTIVE: "/api/v1/leagues/active",
  LEAGUE_BY_ID: (id: string) => `/api/v1/leagues/${id}`,

  // Predictions
  PREDICTIONS_BY_LEAGUE: (leagueId: string) =>
    `/api/v1/predictions/league/${leagueId}`,
  PREDICTION_BY_MATCH: (matchId: string) =>
    `/api/v1/predictions/match/${matchId}`,

  // Matches
  MATCHES_LIVE: "/api/v1/matches/live",
  MATCHES_DAILY: "/api/v1/matches/daily",
  MATCHES_LIVE_WITH_PREDICTIONS: "/api/v1/matches/live/with-predictions",
  MATCHES_BY_TEAM: (teamName: string) => `/api/v1/matches/team/${teamName}`,

  // Suggested Picks
  SUGGESTED_PICKS_BY_MATCH: (matchId: string) =>
    `/api/v1/suggested-picks/match/${matchId}`,
  SUGGESTED_PICKS_FEEDBACK: "/api/v1/suggested-picks/feedback",
  LEARNING_STATS: "/api/v1/suggested-picks/learning-stats",

  // Training
  TRAIN: "/api/v1/train/run-now",
  TRAINING_STATUS: "/api/v1/training/results/latest",

  // Health
  HEALTH: "/health",
} as const;

/**
 * Supported sports and the default sport (backward compatible with football-only).
 */
export type Sport = "soccer" | "tennis" | "baseball" | "basketball";

export const SPORTS: { value: Sport; label: string }[] = [
  { value: "soccer", label: "Fútbol" },
  { value: "tennis", label: "Tenis" },
  { value: "baseball", label: "Béisbol" },
  { value: "basketball", label: "Baloncesto" },
];

export const DEFAULT_SPORT: Sport = "soccer";

/**
 * App Configuration Constants
 */
export const APP_CONFIG = {
  MAX_PARLEY_PICKS: 10,
  LIVE_POLLING_INTERVAL: 30000, // 30 seconds
  // Default timeout for the canonical axios instance (client.ts)
  API_DEFAULT_TIMEOUT: 60000, // 60 seconds
  // Live-with-predictions requests time out at 30s on every path
  LIVE_API_TIMEOUT: 30000, // 30 seconds
  // Suggested-picks generation is slow (AI pick synthesis) — keep 90s
  SUGGESTED_PICKS_TIMEOUT: 90000, // 90 seconds
  TRAINING_TIMEOUT: 300000, // 5 minutes (training runs only once per day)
  // Predictions list default page size (legacy value preserved)
  DEFAULT_PREDICTIONS_LIMIT: 30,
} as const;

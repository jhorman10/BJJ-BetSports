/**
 * API Endpoints Constants
 * Centralized endpoint definitions - single source of truth
 */

export const API_ENDPOINTS = {
  // Leagues
  LEAGUES: "/api/v1/leagues",
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

  // Parleys
  PARLEYS: "/api/v1/parleys/",

  // Training
  TRAIN: "/api/v1/train",
  TRAINING_STATUS: "/api/v1/train/status",

  // Health
  HEALTH: "/health",
} as const;

/**
 * UI Text Constants (Spanish)
 */
export const UI_TEXT = {
  ERRORS: {
    LOAD_PREDICTIONS: "Error al cargar predicciones",
    LOAD_LEAGUES: "Error al cargar ligas",
    LOAD_PICKS: "Error al cargar picks",
    MAX_PARLEY_PICKS: "No puedes agregar más de 10 picks al parley.",
    INSUFFICIENT_DATA: "Datos insuficientes para generar picks",
    LOAD_FAILED: "No se pudieron cargar los datos",
  },
  LOADING: {
    PREDICTIONS: "Cargando predicciones...",
    PICKS: "Cargando picks...",
    LEAGUES: "Cargando ligas...",
  },
  EMPTY: {
    PREDICTIONS: "No hay predicciones disponibles",
    PICKS: "Sin picks disponibles",
    MATCHES: "No hay partidos disponibles",
  },
  LABELS: {
    LOCAL: "Local",
    AWAY: "Visitante",
    DRAW: "Empate",
    PROBABILITY: "Probabilidad",
    CONFIDENCE: "Confianza",
    VALUE_BET: "VALUE BET",
    CORRECT_PREDICTION: "Predicción Correcta",
    WRONG_PREDICTION: "Predicción Errada",
  },
} as const;

/**
 * App Configuration Constants
 */
export const APP_CONFIG = {
  MAX_PARLEY_PICKS: 10,
  LIVE_POLLING_INTERVAL: 30000, // 30 seconds
  API_TIMEOUT: 10000, // 10 seconds
  TRAINING_TIMEOUT: 300000, // 5 minutes
} as const;

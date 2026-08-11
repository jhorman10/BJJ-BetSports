import { MatchPrediction, Prediction } from "../types";

import { normalizeName } from "./searchUtils";

export interface LiveMatchRaw {
  id: string;
  home_team: string;
  home_short_name?: string;
  away_team: string;
  away_short_name?: string;
  league_id: string;
  league_name: string;
  league_flag?: string;
  home_score: number;
  away_score: number;
  status: string;
  minute?: string;
  home_corners: number;
  away_corners: number;
  home_yellow_cards: number;
  away_yellow_cards: number;
  home_red_cards: number;
  away_red_cards: number;
  home_logo_url?: string;
  away_logo_url?: string;
  prediction?: Partial<Prediction>;
}

const getFallbackOutcomeProbabilities = (
  homeScore: number,
  awayScore: number
): Pick<
  Prediction,
  "home_win_probability" | "draw_probability" | "away_win_probability"
> => {
  if (homeScore > awayScore) {
    return {
      home_win_probability: 0.55,
      draw_probability: 0.25,
      away_win_probability: 0.2,
    };
  }

  if (awayScore > homeScore) {
    return {
      home_win_probability: 0.2,
      draw_probability: 0.25,
      away_win_probability: 0.55,
    };
  }

  return {
    home_win_probability: 0.33,
    draw_probability: 0.34,
    away_win_probability: 0.33,
  };
};

const buildPrediction = (
  liveMatch: LiveMatchRaw,
  partialPrediction: Partial<Prediction> = {}
): Prediction => {
  const currentGoals = liveMatch.home_score + liveMatch.away_score;
  const currentCorners = liveMatch.home_corners + liveMatch.away_corners;
  const currentCards =
    liveMatch.home_yellow_cards + liveMatch.away_yellow_cards;
  const fallbackOutcomeProbabilities = getFallbackOutcomeProbabilities(
    liveMatch.home_score,
    liveMatch.away_score
  );

  return {
    id: partialPrediction.id ?? `live-${liveMatch.id}`,
    match_id: partialPrediction.match_id ?? liveMatch.id,
    home_win_probability:
      partialPrediction.home_win_probability ??
      fallbackOutcomeProbabilities.home_win_probability,
    draw_probability:
      partialPrediction.draw_probability ??
      fallbackOutcomeProbabilities.draw_probability,
    away_win_probability:
      partialPrediction.away_win_probability ??
      fallbackOutcomeProbabilities.away_win_probability,
    over_25_probability:
      partialPrediction.over_25_probability ?? (currentGoals > 2.5 ? 1 : 0),
    under_25_probability:
      partialPrediction.under_25_probability ?? (currentGoals > 2.5 ? 0 : 1),
    predicted_home_goals:
      partialPrediction.predicted_home_goals ?? liveMatch.home_score,
    predicted_away_goals:
      partialPrediction.predicted_away_goals ?? liveMatch.away_score,
    predicted_home_corners:
      partialPrediction.predicted_home_corners ?? liveMatch.home_corners,
    predicted_away_corners:
      partialPrediction.predicted_away_corners ?? liveMatch.away_corners,
    predicted_home_yellow_cards:
      partialPrediction.predicted_home_yellow_cards ??
      liveMatch.home_yellow_cards,
    predicted_away_yellow_cards:
      partialPrediction.predicted_away_yellow_cards ??
      liveMatch.away_yellow_cards,
    predicted_home_red_cards:
      partialPrediction.predicted_home_red_cards ?? liveMatch.home_red_cards,
    predicted_away_red_cards:
      partialPrediction.predicted_away_red_cards ?? liveMatch.away_red_cards,
    over_95_corners_probability:
      partialPrediction.over_95_corners_probability ??
      (currentCorners > 9.5 ? 1 : 0),
    under_95_corners_probability:
      partialPrediction.under_95_corners_probability ??
      (currentCorners > 9.5 ? 0 : 1),
    over_45_cards_probability:
      partialPrediction.over_45_cards_probability ??
      (currentCards > 4.5 ? 1 : 0),
    under_45_cards_probability:
      partialPrediction.under_45_cards_probability ??
      (currentCards > 4.5 ? 0 : 1),
    handicap_line: partialPrediction.handicap_line ?? 0,
    handicap_home_probability: partialPrediction.handicap_home_probability ?? 0,
    handicap_away_probability: partialPrediction.handicap_away_probability ?? 0,
    expected_value: partialPrediction.expected_value ?? 0,
    is_value_bet: partialPrediction.is_value_bet ?? false,
    confidence: partialPrediction.confidence ?? 0,
    data_sources: partialPrediction.data_sources ?? ["live_match_fallback"],
    recommended_bet: partialPrediction.recommended_bet ?? "Sin recomendacion",
    over_under_recommendation:
      partialPrediction.over_under_recommendation ?? "Sin recomendacion",
    created_at: partialPrediction.created_at ?? new Date().toISOString(),
    suggested_picks: partialPrediction.suggested_picks,
    highlights_url: partialPrediction.highlights_url,
    real_time_odds: partialPrediction.real_time_odds,
    data_updated_at: partialPrediction.data_updated_at,
    fundamental_analysis: partialPrediction.fundamental_analysis,
  };
};

const wordsMatch = (str1: string, str2: string): boolean => {
  const words1 = str1.split(" ").filter((word) => word.length > 2);
  const words2 = str2.split(" ").filter((word) => word.length > 2);

  if (words1.length > 0 && words2.length > 0) {
    return (
      words1.some((word) => str2.includes(word)) ||
      words2.some((word) => str1.includes(word))
    );
  }

  return str1.includes(str2) || str2.includes(str1);
};

export const matchLiveWithPrediction = (
  liveMatch: LiveMatchRaw,
  predictions: MatchPrediction[]
): MatchPrediction => {
  const matchedPrediction = predictions.find((predictionItem) => {
    const predictionHomeTeam = normalizeName(
      predictionItem.match.home_team.name
    );
    const predictionAwayTeam = normalizeName(
      predictionItem.match.away_team.name
    );
    const liveHomeTeam = normalizeName(liveMatch.home_team);
    const liveAwayTeam = normalizeName(liveMatch.away_team);

    return (
      wordsMatch(predictionHomeTeam, liveHomeTeam) &&
      wordsMatch(predictionAwayTeam, liveAwayTeam)
    );
  });

  const isLivePredictionValid =
    liveMatch.prediction &&
    ((liveMatch.prediction.confidence ?? 0) > 0 ||
      (liveMatch.prediction.home_win_probability ?? 0) > 0);

  const prediction = buildPrediction(liveMatch, {
    ...(matchedPrediction?.prediction ?? {}),
    ...(isLivePredictionValid ? liveMatch.prediction : {}),
  });

  // Convert LiveMatch to MatchPrediction structure
  const matchPrediction: MatchPrediction = {
    match: {
      id: liveMatch.id,
      home_team: {
        id: "0",
        name: liveMatch.home_team,
        short_name: liveMatch.home_short_name,
        logo_url: liveMatch.home_logo_url || "",
      },
      away_team: {
        id: "0",
        name: liveMatch.away_team,
        short_name: liveMatch.away_short_name,
        logo_url: liveMatch.away_logo_url || "",
      },
      match_date: new Date().toISOString(),
      league: {
        id: liveMatch.league_id,
        name: liveMatch.league_name,
        country: "",
        flag: liveMatch.league_flag || "",
      },
      home_goals: liveMatch.home_score,
      away_goals: liveMatch.away_score,
      status: liveMatch.status,
      home_corners: liveMatch.home_corners,
      away_corners: liveMatch.away_corners,
      home_yellow_cards: liveMatch.home_yellow_cards,
      away_yellow_cards: liveMatch.away_yellow_cards,
      home_red_cards: liveMatch.home_red_cards,
      away_red_cards: liveMatch.away_red_cards,
    },
    prediction,
  };

  return matchPrediction;
};

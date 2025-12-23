import { MatchPrediction, SuggestedPick } from "../types";

/**
 * Generate fallback suggested picks based on match prediction data
 * This is used when the backend doesn't return suggested picks
 */
export function generateFallbackPicks(
  matchPrediction: MatchPrediction
): SuggestedPick[] {
  const { prediction } = matchPrediction;
  if (!prediction) return [];

  const picks: SuggestedPick[] = [];

  // Winner pick - highest probability
  const winnerProbs = [
    {
      type: "winner",
      label: "Victoria Local",
      prob: prediction.home_win_probability,
    },
    { type: "draw", label: "Empate", prob: prediction.draw_probability },
    {
      type: "winner",
      label: "Victoria Visitante",
      prob: prediction.away_win_probability,
    },
  ];

  const highestWinner = winnerProbs.reduce((max, current) =>
    current.prob > max.prob ? current : max
  );

  picks.push({
    market_type: highestWinner.type,
    market_label: highestWinner.label,
    probability: highestWinner.prob,
    confidence_level:
      highestWinner.prob > 0.6
        ? "high"
        : highestWinner.prob > 0.45
        ? "medium"
        : "low",
    reasoning: `Probabilidad basada en análisis histórico`,
    risk_level: 1 - highestWinner.prob,
    is_recommended: highestWinner.prob > 0.5,
    priority_score: highestWinner.prob,
  });

  // Over/Under 2.5 goals
  const isOver =
    prediction.over_25_probability > prediction.under_25_probability;
  picks.push({
    market_type: isOver ? "goals_over" : "goals_under",
    market_label: isOver ? "Más de 2.5 Goles" : "Menos de 2.5 Goles",
    probability: isOver
      ? prediction.over_25_probability
      : prediction.under_25_probability,
    confidence_level:
      Math.max(
        prediction.over_25_probability,
        prediction.under_25_probability
      ) > 0.6
        ? "high"
        : "medium",
    reasoning: `${prediction.predicted_home_goals.toFixed(
      1
    )} - ${prediction.predicted_away_goals.toFixed(1)} goles esperados`,
    risk_level:
      1 -
      Math.max(prediction.over_25_probability, prediction.under_25_probability),
    is_recommended:
      Math.max(
        prediction.over_25_probability,
        prediction.under_25_probability
      ) > 0.5,
    priority_score: Math.max(
      prediction.over_25_probability,
      prediction.under_25_probability
    ),
  });

  // Corners if available
  if (
    prediction.over_95_corners_probability !== undefined &&
    prediction.under_95_corners_probability !== undefined
  ) {
    const cornersOver =
      prediction.over_95_corners_probability >
      prediction.under_95_corners_probability;
    picks.push({
      market_type: cornersOver ? "corners_over" : "corners_under",
      market_label: cornersOver ? "Más de 9.5 Corners" : "Menos de 9.5 Corners",
      probability: cornersOver
        ? prediction.over_95_corners_probability
        : prediction.under_95_corners_probability,
      confidence_level:
        Math.max(
          prediction.over_95_corners_probability,
          prediction.under_95_corners_probability
        ) > 0.6
          ? "high"
          : "medium",
      reasoning: "Basado en estadísticas de corners",
      risk_level:
        1 -
        Math.max(
          prediction.over_95_corners_probability,
          prediction.under_95_corners_probability
        ),
      is_recommended:
        Math.max(
          prediction.over_95_corners_probability,
          prediction.under_95_corners_probability
        ) > 0.5,
      priority_score: Math.max(
        prediction.over_95_corners_probability,
        prediction.under_95_corners_probability
      ),
    });
  }

  // Cards if available
  if (
    prediction.over_45_cards_probability !== undefined &&
    prediction.under_45_cards_probability !== undefined
  ) {
    const cardsOver =
      prediction.over_45_cards_probability >
      prediction.under_45_cards_probability;
    picks.push({
      market_type: cardsOver ? "cards_over" : "cards_under",
      market_label: cardsOver ? "Más de 4.5 Tarjetas" : "Menos de 4.5 Tarjetas",
      probability: cardsOver
        ? prediction.over_45_cards_probability
        : prediction.under_45_cards_probability,
      confidence_level:
        Math.max(
          prediction.over_45_cards_probability,
          prediction.under_45_cards_probability
        ) > 0.6
          ? "high"
          : "medium",
      reasoning: "Basado en estadísticas de tarjetas",
      risk_level:
        1 -
        Math.max(
          prediction.over_45_cards_probability,
          prediction.under_45_cards_probability
        ),
      is_recommended:
        Math.max(
          prediction.over_45_cards_probability,
          prediction.under_45_cards_probability
        ) > 0.5,
      priority_score: Math.max(
        prediction.over_45_cards_probability,
        prediction.under_45_cards_probability
      ),
    });
  }

  // Handicap if available
  if (
    prediction.handicap_line !== undefined &&
    prediction.handicap_home_probability !== undefined &&
    prediction.handicap_away_probability !== undefined
  ) {
    const handicapHome =
      prediction.handicap_home_probability >
      prediction.handicap_away_probability;
    picks.push({
      market_type: "va_handicap",
      market_label: handicapHome
        ? `Local ${prediction.handicap_line > 0 ? "+" : ""}${
            prediction.handicap_line
          }`
        : `Visitante ${
            -prediction.handicap_line > 0 ? "+" : ""
          }${-prediction.handicap_line}`,
      probability: handicapHome
        ? prediction.handicap_home_probability
        : prediction.handicap_away_probability,
      confidence_level:
        Math.max(
          prediction.handicap_home_probability,
          prediction.handicap_away_probability
        ) > 0.6
          ? "high"
          : "medium",
      reasoning: "Ventaja/Desventaja calculada",
      risk_level:
        1 -
        Math.max(
          prediction.handicap_home_probability,
          prediction.handicap_away_probability
        ),
      is_recommended:
        Math.max(
          prediction.handicap_home_probability,
          prediction.handicap_away_probability
        ) > 0.55,
      priority_score: Math.max(
        prediction.handicap_home_probability,
        prediction.handicap_away_probability
      ),
    });
  }

  return picks;
}

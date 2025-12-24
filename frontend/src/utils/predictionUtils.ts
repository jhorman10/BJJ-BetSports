import { MatchPrediction, SuggestedPick } from "../types";

/**
 * Genera picks sugeridos basados en las probabilidades de la predicción
 * cuando no hay picks disponibles desde el backend.
 */
export const generateFallbackPicks = (
  matchPrediction: MatchPrediction
): SuggestedPick[] => {
  const picks: SuggestedPick[] = [];
  const { prediction, match } = matchPrediction;

  if (!prediction) return picks;

  // Cast prediction to any to access potential new fields (projected stats)
  const pred = prediction as any;

  // 1. Ganador (Winner)
  if (prediction.home_win_probability > 0.5) {
    picks.push({
      market_type: "winner",
      market_label: `Victoria ${match.home_team.name}`,
      pick_code: "1",
      probability: prediction.home_win_probability,
      confidence_level:
        prediction.home_win_probability > 0.65 ? "high" : "medium",
      reasoning: "Probabilidad favorable para el equipo local.",
      risk_level: 2,
      is_recommended: true,
      priority_score: 1,
      expected_value: 0,
      is_contrarian: false,
    } as any);
  } else if (prediction.away_win_probability > 0.5) {
    picks.push({
      market_type: "winner",
      market_label: `Victoria ${match.away_team.name}`,
      pick_code: "2",
      probability: prediction.away_win_probability,
      confidence_level:
        prediction.away_win_probability > 0.65 ? "high" : "medium",
      reasoning: "Probabilidad favorable para el equipo visitante.",
      risk_level: 2,
      is_recommended: true,
      priority_score: 1,
      expected_value: 0,
      is_contrarian: false,
    } as any);
  }

  // 2. Doble Oportunidad (Double Chance)
  const prob1X = prediction.home_win_probability + prediction.draw_probability;
  const probX2 = prediction.away_win_probability + prediction.draw_probability;

  if (prob1X > 0.75 && prediction.home_win_probability < 0.85) {
    picks.push({
      market_type: "double_chance",
      market_label: `Gana ${match.home_team.name} o Empata`,
      pick_code: "1X",
      probability: prob1X,
      confidence_level: "high",
      reasoning: "Opción segura cubriendo el empate (1X).",
      risk_level: 1,
      is_recommended: true,
      priority_score: 2,
      expected_value: 0,
      is_contrarian: false,
    } as any);
  }

  if (probX2 > 0.75 && prediction.away_win_probability < 0.85) {
    picks.push({
      market_type: "double_chance",
      market_label: `Gana ${match.away_team.name} o Empata`,
      pick_code: "X2",
      probability: probX2,
      confidence_level: "high",
      reasoning: "Opción segura cubriendo el empate (X2).",
      risk_level: 1,
      is_recommended: true,
      priority_score: 2,
      expected_value: 0,
      is_contrarian: false,
    } as any);
  }

  // 3. Goles (Over/Under 2.5)
  if (prediction.over_25_probability > 0.55) {
    picks.push({
      market_type: "goals_over",
      market_label: "Más de 2.5 Goles",
      pick_code: "O2.5",
      probability: prediction.over_25_probability,
      confidence_level:
        prediction.over_25_probability > 0.65 ? "high" : "medium",
      reasoning: "El modelo sugiere un partido con goles.",
      risk_level: 2,
      is_recommended: true,
      priority_score: 1,
      expected_value: 0,
      is_contrarian: false,
    } as any);
  } else if (prediction.under_25_probability > 0.55) {
    picks.push({
      market_type: "goals_under",
      market_label: "Menos de 2.5 Goles",
      pick_code: "U2.5",
      probability: prediction.under_25_probability,
      confidence_level:
        prediction.under_25_probability > 0.65 ? "high" : "medium",
      reasoning: "El modelo sugiere un partido cerrado.",
      risk_level: 2,
      is_recommended: true,
      priority_score: 1,
      expected_value: 0,
      is_contrarian: false,
    } as any);
  }

  // 4. Ambos Marcan (BTTS) - Fallback logic matching backend approximation
  if (prediction.predicted_home_goals && prediction.predicted_away_goals) {
    // P(score) = 1 - e^(-lambda)
    const probHome = 1 - Math.exp(-prediction.predicted_home_goals);
    const probAway = 1 - Math.exp(-prediction.predicted_away_goals);
    const probBTTS = probHome * probAway;

    if (probBTTS > 0.6) {
      picks.push({
        market_type: "btts_yes",
        market_label: "Ambos Marcan: Sí",
        pick_code: "BTTS-Y",
        probability: probBTTS,
        confidence_level: probBTTS > 0.7 ? "high" : "medium",
        reasoning: "Alta probabilidad estadística de goles para ambos equipos.",
        risk_level: 2,
        is_recommended: true,
        priority_score: 1.5,
        expected_value: 0,
        is_contrarian: false,
      } as any);
    }
  }

  // 5. Corners (Over/Under) - Usando proyecciones del backend
  if (
    pred.predicted_home_corners !== undefined &&
    pred.predicted_away_corners !== undefined
  ) {
    const totalCorners =
      pred.predicted_home_corners + pred.predicted_away_corners;
    if (totalCorners > 9.5) {
      picks.push({
        market_type: "corners_over",
        market_label: "Más de 9.5 Córners",
        pick_code: "O9.5C",
        probability: 0.65, // Estimado si no viene del back
        confidence_level: "medium",
        reasoning:
          "Proyección alta de córners basada en estadísticas históricas.",
        risk_level: 2,
        is_recommended: true,
        priority_score: 2,
        expected_value: 0,
        is_contrarian: false,
      } as any);
    }
  }

  // 6. Cards (Over/Under) - Usando proyecciones del backend
  if (
    pred.predicted_home_yellow_cards !== undefined &&
    pred.predicted_away_yellow_cards !== undefined
  ) {
    const totalCards =
      pred.predicted_home_yellow_cards + pred.predicted_away_yellow_cards;
    if (totalCards > 4.5) {
      picks.push({
        market_type: "cards_over",
        market_label: "Más de 4.5 Tarjetas",
        pick_code: "O4.5Y",
        probability: 0.6,
        confidence_level: "medium",
        reasoning: "Partido con proyección de alta fricción y tarjetas.",
        risk_level: 2,
        is_recommended: true,
        priority_score: 2,
        expected_value: 0,
        is_contrarian: false,
      } as any);
    }
  }

  return picks;
};

/**
 * Obtiene el mejor pick disponible para una predicción.
 * Retorna el pick con mayor probabilidad, igual a como se muestra en el modal de detalles.
 */
export const getBestPick = (
  matchPrediction: MatchPrediction,
  existingPicks: SuggestedPick[] = []
): SuggestedPick | null => {
  let picks = [...existingPicks];

  // Si no hay picks existentes, intentamos generarlos
  if (picks.length === 0) {
    picks = generateFallbackPicks(matchPrediction);
  }

  if (picks.length === 0) return null;

  // Ordenar por probabilidad descendente y retornar el primero
  // Esto coincide con el orden mostrado en el modal de SuggestedPicksTab
  return picks.sort((a, b) => b.probability - a.probability)[0];
};

/**
 * Shared utilities for market visualization and logic
 */

import { SuggestedPick } from "../types";

/**
 * Returns the uppercase category for a given market type.
 * Consolidates categorization logic used across BotDashboard,
 * SuggestedPicksTab, and MatchHistoryTable into a single source of truth.
 */
export const getMarketCategory = (marketType: string): string => {
  const type = marketType.toUpperCase();
  if (type.includes("CORNER")) return "CORNERS";
  if (type.includes("CARD") || type.includes("TARJETA")) return "CARDS";
  if (type.includes("HANDICAP")) return "HANDICAPS";
  if (type.includes("BTTS") || type.includes("AMBOS")) return "BTTS";
  if (
    type.includes("DOUBLE") ||
    type.includes("CHANCE") ||
    type.includes("DOBLE")
  )
    return "DOUBLE_CHANCE";
  if (
    type.includes("WIN") ||
    type.includes("DRAW") ||
    type.includes("RESULT") ||
    type.includes("1X2")
  )
    return "WINNER";
  if (
    type.includes("GOAL") ||
    type.includes("GOL") ||
    type.includes("OVER") ||
    type.includes("UNDER")
  ) {
    return "GOALS";
  }
  return "OTHER";
};

export const getPickColor = (probability: number): string => {
  if (probability > 0.7) return "#22c55e";
  if (probability > 0.5) return "#f59e0b";
  return "#ef4444";
};

export const getMarketIcon = (marketType: string): string => {
  switch (marketType) {
    case "corners_over":
    case "corners_under":
    case "home_corners_over":
    case "home_corners_under":
    case "away_corners_over":
    case "away_corners_under":
      return "⛳";
    case "cards_over":
    case "cards_under":
    case "home_cards_over":
    case "home_cards_under":
    case "away_cards_over":
    case "away_cards_under":
      return "🟨";
    case "red_cards":
      return "🟥";
    case "va_handicap":
      return "⚖️";
    case "winner":
      return "🏆";
    case "double_chance":
    case "double_chance_1x":
    case "double_chance_x2":
    case "double_chance_12":
      return "🛡️";
    case "draw":
      return "🤝";
    case "goals_over":
    case "goals_under":
    case "team_goals_over":
    case "team_goals_under":
    case "goals_over_0_5":
    case "goals_over_1_5":
    case "goals_over_2_5":
    case "goals_over_3_5":
    case "goals_under_0_5":
    case "goals_under_1_5":
    case "goals_under_2_5":
    case "goals_under_3_5":
      return "⚽";
    case "btts_yes":
    case "btts_no":
      return "🥅";
    default:
      return "📊";
  }
};

export const getUniquePicks = (picks: SuggestedPick[] = []): SuggestedPick[] => {
  if (!picks) return [];

  // First sort by confidence/probability descending to ensure we keep the best version
  const sortedPicks = [...picks].sort(
    (a, b) =>
      (b.confidence || b.probability || 0) -
      (a.confidence || a.probability || 0)
  );

  const seen = new Set<string>();
  const unique = sortedPicks.filter((pick) => {
    const key = `${pick.market_type}-${pick.market_label}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  return unique;
};

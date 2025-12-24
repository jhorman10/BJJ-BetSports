/**
 * Shared utilities for market visualization and logic
 */

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
    case "away_corners_over":
      return "⚑";
    case "cards_over":
    case "cards_under":
    case "home_cards_over":
    case "away_cards_over":
      return "🟨";
    case "red_cards":
      return "🟥";
    case "va_handicap":
      return "⚖️";
    case "winner":
      return "🏆";
    case "double_chance":
      return "🛡️";
    case "draw":
      return "🤝";
    case "goals_over":
    case "goals_under":
    case "team_goals_over":
    case "team_goals_under":
      return "⚽";
    case "btts_yes":
    case "btts_no":
      return "🥅";
    default:
      return "📊";
  }
};

export const getUniquePicks = (picks: any[]) => {
  if (!picks) return [];
  const seen = new Set();
  const unique = picks.filter((pick) => {
    const key = `${pick.market_type}-${pick.market_label}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  // Sort by confidence or probability, whichever is available
  return unique.sort(
    (a, b) =>
      (b.confidence || b.probability || 0) -
      (a.confidence || a.probability || 0)
  );
};

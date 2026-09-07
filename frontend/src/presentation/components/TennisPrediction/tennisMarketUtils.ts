import { TennisMarket } from "../../../types";

// Market categories for tennis
export type TennisMarketCategory =
  | "MATCH_WINNER"
  | "SET_BETS"
  | "TOTAL_SETS"
  | "FIRST_SET"
  | "CORRECT_SCORE"
  | "TOTAL_GAMES";

export interface TennisCategoryTab {
  key: TennisMarketCategory;
  label: string;
  icon: string;
}

export const TENNIS_CATEGORY_TABS: TennisCategoryTab[] = [
  { key: "MATCH_WINNER", label: "Ganador", icon: "🏆" },
  { key: "SET_BETS", label: "Hándicap Sets", icon: "📊" },
  { key: "TOTAL_SETS", label: "Total Sets", icon: "🔢" },
  { key: "FIRST_SET", label: "Primer Set", icon: "1️⃣" },
  { key: "CORRECT_SCORE", label: "Resultado", icon: "🎯" },
  { key: "TOTAL_GAMES", label: "Total Juegos", icon: "🎾" },
];

// Map market_type to category
export function getMarketCategory(marketType: string): TennisMarketCategory {
  const mapping: Record<string, TennisMarketCategory> = {
    match_winner: "MATCH_WINNER",
    set_handicap: "SET_BETS",
    total_sets_over: "TOTAL_SETS",
    total_sets_under: "TOTAL_SETS",
    first_set_winner: "FIRST_SET",
    correct_score: "CORRECT_SCORE",
    total_games_over: "TOTAL_GAMES",
    total_games_under: "TOTAL_GAMES",
  };
  return mapping[marketType] || "MATCH_WINNER";
}

// Get market icon
export function getMarketIcon(marketType: string): string {
  const icons: Record<string, string> = {
    match_winner: "🏆",
    set_handicap: "📊",
    total_sets_over: "📈",
    total_sets_under: "📉",
    first_set_winner: "1️⃣",
    correct_score: "🎯",
    total_games_over: "📈",
    total_games_under: "📉",
  };
  return icons[marketType] || "🎾";
}

// Get confidence color
export function getConfidenceColor(level: string): string {
  switch (level) {
    case "high":
      return "#10b981";
    case "medium":
      return "#f59e0b";
    case "low":
      return "#ef4444";
    default:
      return "#6b7280";
  }
}

// Get probability bar color
export function getProbabilityColor(prob: number): string {
  if (prob > 0.7) return "#10b981";
  if (prob > 0.5) return "#f59e0b";
  return "#ef4444";
}

// Group markets by category
export function groupMarketsByCategory(markets: TennisMarket[]): Map<TennisMarketCategory, TennisMarket[]> {
  const grouped = new Map<TennisMarketCategory, TennisMarket[]>();
  
  for (const tab of TENNIS_CATEGORY_TABS) {
    grouped.set(tab.key, []);
  }
  
  for (const market of markets) {
    const category = getMarketCategory(market.market_type);
    const list = grouped.get(category);
    if (list) {
      list.push(market);
    }
  }
  
  return grouped;
}

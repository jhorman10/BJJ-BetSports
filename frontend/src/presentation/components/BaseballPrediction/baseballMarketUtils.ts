import { BaseballMarket } from "../../../types";

// Market categories for baseball
export type BaseballMarketCategory =
  | "MONEYLINE"
  | "RUN_LINE"
  | "TOTAL_RUNS"
  | "FIRST_5"
  | "TEAM_TOTAL"
  | "BTS";

export interface BaseballCategoryTab {
  key: BaseballMarketCategory;
  label: string;
  icon: string;
}

export const BASEBALL_CATEGORY_TABS: BaseballCategoryTab[] = [
  { key: "MONEYLINE", label: "Moneyline", icon: "⚾" },
  { key: "RUN_LINE", label: "Run Line", icon: "📊" },
  { key: "TOTAL_RUNS", label: "Total Carreras", icon: "🔢" },
  { key: "FIRST_5", label: "Primeros 5", icon: "5️⃣" },
  { key: "TEAM_TOTAL", label: "Total Equipo", icon: "🏏" },
  { key: "BTS", label: "Ambos Anotan", icon: "💯" },
];

// Map market_type to category
export function getMarketCategory(marketType: string): BaseballMarketCategory {
  const mapping: Record<string, BaseballMarketCategory> = {
    moneyline: "MONEYLINE",
    run_line: "RUN_LINE",
    total_runs_over: "TOTAL_RUNS",
    total_runs_under: "TOTAL_RUNS",
    first_5_innings: "FIRST_5",
    team_total_runs: "TEAM_TOTAL",
    both_teams_score: "BTS",
    both_teams_score_no: "BTS",
  };
  return mapping[marketType] || "MONEYLINE";
}

// Get market icon
export function getMarketIcon(marketType: string): string {
  const icons: Record<string, string> = {
    moneyline: "⚾",
    run_line: "📊",
    total_runs_over: "📈",
    total_runs_under: "📉",
    first_5_innings: "5️⃣",
    team_total_runs: "🏏",
    both_teams_score: "💯",
    both_teams_score_no: "🚫",
  };
  return icons[marketType] || "⚾";
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
export function groupMarketsByCategory(markets: BaseballMarket[]): Map<BaseballMarketCategory, BaseballMarket[]> {
  const grouped = new Map<BaseballMarketCategory, BaseballMarket[]>();
  for (const tab of BASEBALL_CATEGORY_TABS) {
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

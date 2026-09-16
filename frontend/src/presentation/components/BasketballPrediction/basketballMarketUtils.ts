import { BasketballMarket } from "../../../types";

// Market categories for basketball
export type BasketballMarketCategory =
  | "MONEYLINE"
  | "SPREAD"
  | "TOTAL"
  | "FIRST_HALF"
  | "FIRST_QUARTER"
  | "TEAM_TOTAL";

export interface BasketballCategoryTab {
  key: BasketballMarketCategory;
  label: string;
  icon: string;
}

export const BASKETBALL_CATEGORY_TABS: BasketballCategoryTab[] = [
  { key: "MONEYLINE", label: "Moneyline", icon: "🏀" },
  { key: "SPREAD", label: "Spread", icon: "📊" },
  { key: "TOTAL", label: "Total O/U", icon: "🔢" },
  { key: "FIRST_HALF", label: "1H Moneyline", icon: "🕑" },
  { key: "FIRST_QUARTER", label: "1Q Moneyline", icon: "1️⃣" },
  { key: "TEAM_TOTAL", label: "Team Total", icon: "🎯" },
];

// Map market_type to category
export function getMarketCategory(marketType: string): BasketballMarketCategory {
  const mapping: Record<string, BasketballMarketCategory> = {
    moneyline: "MONEYLINE",
    spread: "SPREAD",
    total_over: "TOTAL",
    total_under: "TOTAL",
    first_half_moneyline: "FIRST_HALF",
    first_quarter_moneyline: "FIRST_QUARTER",
    team_total: "TEAM_TOTAL",
  };
  return mapping[marketType] || "MONEYLINE";
}

// Get market icon
export function getMarketIcon(marketType: string): string {
  const icons: Record<string, string> = {
    moneyline: "🏀",
    spread: "📊",
    total_over: "📈",
    total_under: "📉",
    first_half_moneyline: "🕑",
    first_quarter_moneyline: "1️⃣",
    team_total: "🎯",
  };
  return icons[marketType] || "🏀";
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
export function groupMarketsByCategory(markets: BasketballMarket[]): Map<BasketballMarketCategory, BasketballMarket[]> {
  const grouped = new Map<BasketballMarketCategory, BasketballMarket[]>();
  for (const tab of BASKETBALL_CATEGORY_TABS) {
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

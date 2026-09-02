import { MatchPredictionHistory } from "../../../types";
import { getMarketCategory } from "../../../utils/marketUtils";

export interface MarketStats {
  market_type: string;
  market_label: string;
  total: number;
  won: number;
  lost: number;
  accuracy: number;
}

export const calculateMarketStats = (
  matches: MatchPredictionHistory[]
): MarketStats[] => {
  const categories: Record<
    string,
    { total: number; won: number; lost: number; label: string }
  > = {
    WINNER: { total: 0, won: 0, lost: 0, label: "Ganador del Partido (1X2)" },
    DOUBLE_CHANCE: { total: 0, won: 0, lost: 0, label: "Doble Oportunidad" },
    GOALS: { total: 0, won: 0, lost: 0, label: "Goles (Más/Menos)" },
    BTTS: { total: 0, won: 0, lost: 0, label: "Ambos Marcan" },
    CORNERS: { total: 0, won: 0, lost: 0, label: "Córners" },
    CARDS: { total: 0, won: 0, lost: 0, label: "Tarjetas" },
    HANDICAPS: { total: 0, won: 0, lost: 0, label: "Hándicap" },
  };

  for (const match of matches) {
    if (match.picks) {
      for (const pick of match.picks) {
        if (pick.was_correct === undefined) continue;
        const categoryKey = getMarketCategory(pick.market_type || "");
        if (categories[categoryKey]) {
          categories[categoryKey].total++;
          if (pick.was_correct) {
            categories[categoryKey].won++;
          } else {
            categories[categoryKey].lost++;
          }
        }
      }
    }
  }

  return Object.entries(categories)
    .reduce<MarketStats[]>((acc, [key, value]) => {
      if (value.total > 0) {
        acc.push({
          market_type: key,
          market_label: value.label,
          total: value.total,
          won: value.won,
          lost: value.lost,
          accuracy: (value.won / value.total) * 100,
        });
      }
      return acc;
    }, [])
    .sort((a, b) => b.total - a.total);
};

export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString("es-CO", {
    timeZone: "America/Bogota",
    day: "numeric",
    month: "short",
  });
};

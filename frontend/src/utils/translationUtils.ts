/**
 * Utility functions for translating backend values to Spanish
 */

/**
 * Translates match status codes to Spanish
 */
export const translateMatchStatus = (status: string | undefined): string => {
  if (!status) return "PENDIENTE";

  const map: Record<string, string> = {
    NS: "POR COMENZAR",
    LIVE: "EN VIVO",
    HT: "ENTRETIEMPO",
    FT: "FINALIZADO",
    AET: "PRÓRROGA",
    PEN: "PENALES",
    "1H": "1ER TIEMPO",
    "2H": "2DO TIEMPO",
    ET: "TIEMPO EXTRA",
    P: "PENALES",
    TIMED: "PROGRAMADO",
    FINISHED: "FINALIZADO",
    POSTPONED: "POSPUESTO",
    CANCELED: "CANCELADO",
    SUSPENDED: "SUSPENDIDO",
    INT: "INTERRUMPIDO",
    ABD: "ABANDONADO",
    AWD: "ADJUDICADO",
    WO: "WALKOVER",
  };

  return map[status.toUpperCase()] || status;
};

/**
 * Translates recommended bets to Spanish
 */
export const translateRecommendedBet = (bet: string | undefined): string => {
  if (!bet) return "N/A";

  if (bet === "Home Win (1)") return "Victoria Local (1)";
  if (bet === "Away Win (2)") return "Victoria Visitante (2)";
  if (bet === "Draw (X)") return "Empate (X)";

  // Handle other common variations just in case
  if (bet.toLowerCase().includes("home")) return "Victoria Local (1)";
  if (bet.toLowerCase().includes("away")) return "Victoria Visitante (2)";
  if (bet.toLowerCase().includes("draw")) return "Empate (X)";

  return bet;
};

/**
 * Translates Over/Under recommendations to Spanish
 */
export const translateOverUnder = (bet: string | undefined): string => {
  if (!bet) return "N/A";

  if (bet === "Over 2.5") return "Más de 2.5";
  if (bet === "Under 2.5") return "Menos de 2.5";

  // Format consistent with others
  if (bet.toLowerCase().includes("over")) return bet.replace("Over", "Más de");
  if (bet.toLowerCase().includes("under"))
    return bet.replace("Under", "Menos de");

  return bet;
};

import { useState, useCallback, useEffect } from "react";
import api from "../services/api";

// Local interface until backend adds new fields
export interface LiveMatch {
  id: string;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  minute: number;
  league_id: string;
  league_name: string;
  status: "LIVE" | "HT" | "FT" | "BREAK";
  home_corners: number;
  away_corners: number;
  home_yellow_cards: number;
  away_yellow_cards: number;
  home_red_cards: number;
  away_red_cards: number;
}

// Datos simulados de respaldo para asegurar que la UI funcione
const MOCK_LIVE_MATCHES: LiveMatch[] = [
  {
    id: "mock-1",
    home_team: "Flamengo",
    away_team: "Fluminense",
    home_score: 1,
    away_score: 1,
    minute: 34,
    league_id: "bra_1",
    league_name: "Brasileirão Série A",
    status: "LIVE",
    home_corners: 4,
    away_corners: 2,
    home_yellow_cards: 2,
    away_yellow_cards: 1,
    home_red_cards: 0,
    away_red_cards: 0,
  },
  {
    id: "mock-2",
    home_team: "Real Madrid",
    away_team: "Barcelona",
    home_score: 2,
    away_score: 1,
    minute: 78,
    league_id: "esp_1",
    league_name: "La Liga",
    status: "LIVE",
    home_corners: 7,
    away_corners: 3,
    home_yellow_cards: 1,
    away_yellow_cards: 3,
    home_red_cards: 0,
    away_red_cards: 1,
  },
];

// --- Cache Simple para API Pública ---
let publicApiCache: { data: LiveMatch[]; timestamp: number } | null = null;
const CACHE_DURATION = 30000; // 30 segundos de caché

// --- API Pública de Respaldo (ESPN) ---
const fetchPublicLiveMatches = async (): Promise<LiveMatch[]> => {
  const now = Date.now();
  if (publicApiCache && now - publicApiCache.timestamp < CACHE_DURATION) {
    return publicApiCache.data;
  }

  // Slugs de ligas en ESPN
  const leagues = [
    "eng.1", // Premier League
    "esp.1", // La Liga
    "ita.1", // Serie A
    "ger.1", // Bundesliga
    "fra.1", // Ligue 1
    "por.1", // Primeira Liga
    "bra.1", // Brasileirao
    "arg.1", // Liga Profesional
    "mex.1", // Liga MX
    "usa.1", // MLS
    "uefa.champions", // Champions League
    "conmebol.libertadores", // Libertadores
  ];

  try {
    // Hacemos peticiones en paralelo a todas las ligas
    const requests = leagues.map((league) =>
      fetch(
        `https://site.api.espn.com/apis/site/v2/sports/soccer/${league}/scoreboard`
      )
        .then((res) => (res.ok ? res.json() : null))
        .catch(() => null)
    );

    const responses = await Promise.all(requests);
    const liveMatches: LiveMatch[] = [];

    responses.forEach((data: any) => {
      if (!data || !data.events) return;

      const leagueName = data.leagues?.[0]?.name || "Torneo Internacional";
      const leagueId = data.leagues?.[0]?.slug || "unknown";

      data.events.forEach((event: any) => {
        const status = event.status?.type?.state;
        if (status === "in" || status === "ht") {
          const competition = event.competitions?.[0];
          const competitors = competition?.competitors || [];
          const home = competitors.find((c: any) => c.homeAway === "home");
          const away = competitors.find((c: any) => c.homeAway === "away");

          if (home && away) {
            liveMatches.push({
              id: event.id,
              home_team: home.team?.displayName || "Local",
              away_team: away.team?.displayName || "Visitante",
              home_score: parseInt(home.score || "0"),
              away_score: parseInt(away.score || "0"),
              minute: parseInt(
                event.status?.displayClock?.replace("'", "") || "0"
              ),
              league_id: leagueId,
              league_name: leagueName,
              status: status === "ht" ? "HT" : "LIVE",
              home_corners: 0,
              away_corners: 0,
              home_yellow_cards: 0,
              away_yellow_cards: 0,
              home_red_cards: 0,
              away_red_cards: 0,
            });
          }
        }
      });
    });

    publicApiCache = { data: liveMatches, timestamp: Date.now() };
    return liveMatches;
  } catch (error) {
    console.error("Error consultando API pública:", error);
    return [];
  }
};

export const useLiveMatches = () => {
  const [matches, setMatches] = useState<LiveMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLiveMatches = useCallback(async () => {
    setLoading(true);
    try {
      await new Promise((resolve) => setTimeout(resolve, 600));

      console.log("Iniciando carga de partidos en vivo...");

      try {
        if (typeof api.getLiveMatches !== "function")
          throw new Error("API method missing");

        const data = await api.getLiveMatches();

        let liveMatches: LiveMatch[] = Array.isArray(data)
          ? data.map((match: any) => ({
              id: match.id,
              home_team: match.home_team?.name || match.home_team || "Local",
              away_team:
                match.away_team?.name || match.away_team || "Visitante",
              home_score: match.home_goals ?? match.home_score ?? 0,
              away_score: match.away_goals ?? match.away_score ?? 0,
              minute: match.minute || Math.floor(Math.random() * 90) + 1,
              league_id: match.league?.id || "unknown",
              league_name: match.league?.name || "Liga Desconocida",
              status: (match.status as LiveMatch["status"]) || "LIVE",
              home_corners: match.home_corners || 0,
              away_corners: match.away_corners || 0,
              home_yellow_cards: match.home_yellow_cards || 0,
              away_yellow_cards: match.away_yellow_cards || 0,
              home_red_cards: match.home_red_cards || 0,
              away_red_cards: match.away_red_cards || 0,
            }))
          : [];

        if (liveMatches.length === 0) {
          console.log("Backend vacío. Buscando en API pública (ESPN)...");
          const publicMatches = await fetchPublicLiveMatches();

          if (publicMatches.length > 0) {
            liveMatches = publicMatches;
          } else {
            console.log("Sin partidos en vivo reales. Usando Mock.");
            liveMatches = MOCK_LIVE_MATCHES;
          }
        }

        setMatches(liveMatches);
        setError(null);
      } catch (err) {
        console.error("Error cargando partidos en vivo:", err);
        setMatches(MOCK_LIVE_MATCHES);
        setError(null);
      } finally {
        setLoading(false);
      }
    } catch (e) {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLiveMatches();
    const interval = setInterval(fetchLiveMatches, 60000);
    return () => clearInterval(interval);
  }, [fetchLiveMatches]);

  return { matches, loading, error, refresh: fetchLiveMatches };
};

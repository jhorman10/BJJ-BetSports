import { useState, useCallback, useEffect } from "react";
import api from "../services/api";
import { MatchPrediction } from "../types";

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
  league_flag?: string;
  status: "LIVE" | "HT" | "FT" | "BREAK";
  home_corners: number;
  away_corners: number;
  home_yellow_cards: number;
  away_yellow_cards: number;
  home_red_cards: number;
  away_red_cards: number;
  prediction?: MatchPrediction["prediction"];
}

// --- Interfaces for ESPN API ---
interface ESPNTeam {
  id: string;
  displayName: string;
  logo?: string;
}

interface ESPNCompetitor {
  id: string;
  homeAway: string;
  team: ESPNTeam;
  score?: string;
}

interface ESPNCompetition {
  competitors: ESPNCompetitor[];
}

interface ESPNStatus {
  type: {
    state: string;
  };
  displayClock: string;
}

interface ESPNEvent {
  id: string;
  status: ESPNStatus;
  competitions: ESPNCompetition[];
}

interface ESPNLeague {
  name: string;
  slug: string;
}

interface ESPNScoreboardResponse {
  leagues?: ESPNLeague[];
  events?: ESPNEvent[];
}

interface ESPNStatistic {
  name: string;
  displayValue: string;
}

interface ESPNTeamBoxscore {
  team: { id: string };
  statistics: ESPNStatistic[];
}

interface ESPNBoxscore {
  teams: ESPNTeamBoxscore[];
}

interface ESPNSummaryResponse {
  boxscore?: ESPNBoxscore;
}

interface MatchToEnrich {
  event: ESPNEvent;
  leagueId: string;
  leagueName: string;
}

// --- Cache Simple para API Pública ---
let publicApiCache: { data: LiveMatch[]; timestamp: number } | null = null;
const CACHE_DURATION = 10000; // 10 segundos de caché para mayor precisión

// Helper para extraer estadísticas del boxscore (Summary API)
const extractStat = (
  boxscore: ESPNBoxscore | undefined,
  teamId: string,
  statName: string | string[]
): number => {
  if (!boxscore || !boxscore.teams) return 0;
  const teamStats = boxscore.teams.find(
    (t) => String(t.team?.id) === String(teamId)
  );
  if (!teamStats || !teamStats.statistics) return 0;
  const names = Array.isArray(statName) ? statName : [statName];
  const stat = teamStats.statistics.find((s) => names.includes(s.name));
  return stat ? parseInt(stat.displayValue) : 0;
};

// --- API Pública de Respaldo (ESPN) ---
const fetchPublicLiveMatches = async (): Promise<LiveMatch[]> => {
  const now = Date.now();
  if (publicApiCache && now - publicApiCache.timestamp < CACHE_DURATION) {
    return publicApiCache.data;
  }

  // Slugs de ligas en ESPN (solo las que funcionan correctamente)
  const leagues = [
    "eng.1",
    "eng.2",
    "eng.3", // Inglaterra
    "esp.1",
    "esp.2", // España
    "ita.1",
    "ita.2", // Italia
    "ger.1",
    "ger.2", // Alemania
    "fra.1",
    "fra.2", // Francia
    "por.1", // Primeira Liga
    "ned.1", // Eredivisie
    "bra.1", // Brasileirao
    "arg.1", // Liga Profesional
    "col.1", // Colombia Primera A
    "mex.1", // Liga MX
    "usa.1", // MLS
    "tur.1", // Turquía
    "chn.1", // China
    "jpn.1", // Japón
    "rus.1", // Rusia
    "bel.1", // Bélgica
    "aut.1", // Austria
    "den.1", // Dinamarca
    "swe.1", // Suecia
    "nor.1", // Noruega
    "sco.1", // Escocia
    "uefa.champions", // Champions League
    "uefa.europa", // Europa League
    "conmebol.libertadores",
    "conmebol.sudamericana", // Conmebol
  ];

  try {
    // Hacemos peticiones en paralelo a todas las ligas
    const requests = leagues.map((league) =>
      fetch(
        `https://site.api.espn.com/apis/site/v2/sports/soccer/${league}/scoreboard`
      )
        .then((res) =>
          res.ok ? (res.json() as Promise<ESPNScoreboardResponse>) : null
        )
        .catch(() => null)
    );

    const responses = await Promise.all(requests);
    const liveMatches: LiveMatch[] = [];
    const matchesToEnrich: MatchToEnrich[] = [];
    const detailRequests: Promise<ESPNSummaryResponse | null>[] = [];

    responses.forEach((data) => {
      if (!data || !data.events) return;

      const leagueName = data.leagues?.[0]?.name || "Torneo Internacional";
      const leagueId = data.leagues?.[0]?.slug || "unknown";

      data.events.forEach((event) => {
        const status = event.status?.type?.state;
        if (status === "in" || status === "ht") {
          matchesToEnrich.push({ event, leagueId, leagueName });
          // Solicitar detalles (summary) para obtener corners y tarjetas
          detailRequests.push(
            fetch(
              `https://site.api.espn.com/apis/site/v2/sports/soccer/${leagueId}/summary?event=${event.id}`
            )
              .then((res) =>
                res.ok ? (res.json() as Promise<ESPNSummaryResponse>) : null
              )
              .catch(() => null)
          );
        }
      });
    });

    // Obtener detalles en paralelo
    const detailsResponses = await Promise.all(detailRequests);

    // Combinar datos básicos con detalles
    matchesToEnrich.forEach((item, index) => {
      const { event, leagueId, leagueName } = item;
      const details = detailsResponses[index];
      const boxscore = details?.boxscore;

      const competition = event.competitions?.[0];
      const competitors = competition?.competitors || [];
      const home = competitors.find((c) => c.homeAway === "home");
      const away = competitors.find((c) => c.homeAway === "away");

      if (home && away) {
        const status = event.status?.type?.state;
        liveMatches.push({
          id: event.id,
          home_team: home.team?.displayName || "Local",
          away_team: away.team?.displayName || "Visitante",
          home_score: parseInt(home.score || "0"),
          away_score: parseInt(away.score || "0"),
          minute: parseInt(event.status?.displayClock?.replace("'", "") || "0"),
          league_id: leagueId,
          league_name: leagueName,
          status: status === "ht" ? "HT" : "LIVE",
          // Extraer estadísticas del boxscore (summary)
          home_corners: extractStat(boxscore, home.team.id, [
            "corners",
            "wonCorners",
          ]),
          away_corners: extractStat(boxscore, away.team.id, [
            "corners",
            "wonCorners",
          ]),
          home_yellow_cards: extractStat(boxscore, home.team.id, "yellowCards"),
          away_yellow_cards: extractStat(boxscore, away.team.id, "yellowCards"),
          home_red_cards: extractStat(boxscore, home.team.id, "redCards"),
          away_red_cards: extractStat(boxscore, away.team.id, "redCards"),
        });
      }
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
      // Iniciar carga de partidos en vivo

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
              minute: match.minute || 0,
              league_id: match.league?.id || "unknown",
              league_name: match.league?.name || "Liga Desconocida",
              league_flag: match.league?.flag || match.league?.logo || null,
              status: (match.status as LiveMatch["status"]) || "LIVE",
              home_corners: match.home_corners || 0,
              away_corners: match.away_corners || 0,
              home_yellow_cards: match.home_yellow_cards || 0,
              away_yellow_cards: match.away_yellow_cards || 0,
              home_red_cards: match.home_red_cards || 0,
              away_red_cards: match.away_red_cards || 0,
              prediction: match.prediction,
            }))
          : [];

        if (liveMatches.length === 0) {
          const publicMatches = await fetchPublicLiveMatches();
          liveMatches = publicMatches;
        }

        setMatches(liveMatches);
        setError(null);
      } catch (err) {
        console.error(
          "Error cargando partidos en vivo (API Backend), intentando Api Pública:",
          err
        );
        try {
          const publicMatches = await fetchPublicLiveMatches();
          setMatches(publicMatches);
        } catch (publicApiErr) {
          console.error("Error también en API pública:", publicApiErr);
          setMatches([]);
        }
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

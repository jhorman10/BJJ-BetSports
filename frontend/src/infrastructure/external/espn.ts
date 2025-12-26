import { LiveMatchPrediction } from "../../domain/entities";

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
let publicApiCache: { data: LiveMatchPrediction[]; timestamp: number } | null =
  null;
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
export const fetchESPNLiveMatches = async (): Promise<
  LiveMatchPrediction[]
> => {
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
    const liveMatches: LiveMatchPrediction[] = [];
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

        // Construct the LiveMatchPrediction object manually to match domain entity
        liveMatches.push({
          match: {
            id: event.id,
            home_team: {
              id: home.team.id,
              name: home.team?.displayName || "Local",
            },
            away_team: {
              id: away.team.id,
              name: away.team?.displayName || "Visitante",
            },
            league: { id: leagueId, name: leagueName, country: "" },
            match_date: new Date().toISOString(), // Approximation
            home_goals: parseInt(home.score || "0"),
            away_goals: parseInt(away.score || "0"),
            status: status === "ht" ? "HT" : "LIVE",
            home_corners: extractStat(boxscore, home.team.id, [
              "corners",
              "wonCorners",
            ]),
            away_corners: extractStat(boxscore, away.team.id, [
              "corners",
              "wonCorners",
            ]),
            home_yellow_cards: extractStat(
              boxscore,
              home.team.id,
              "yellowCards"
            ),
            away_yellow_cards: extractStat(
              boxscore,
              away.team.id,
              "yellowCards"
            ),
            home_red_cards: extractStat(boxscore, home.team.id, "redCards"),
            away_red_cards: extractStat(boxscore, away.team.id, "redCards"),
            minute: event.status.displayClock,
            // Extended Stats
            home_possession:
              extractStat(boxscore, home.team.id, [
                "possessionPct",
                "possession",
              ]) + "%",
            away_possession:
              extractStat(boxscore, away.team.id, [
                "possessionPct",
                "possession",
              ]) + "%",
            home_shots_on_target: extractStat(boxscore, home.team.id, [
              "shotsOnGoal",
              "ontargetScoringAttempts",
            ]),
            away_shots_on_target: extractStat(boxscore, away.team.id, [
              "shotsOnGoal",
              "ontargetScoringAttempts",
            ]),
            home_total_shots: extractStat(boxscore, home.team.id, [
              "totalShots",
              "sh",
            ]),
            away_total_shots: extractStat(boxscore, away.team.id, [
              "totalShots",
              "sh",
            ]),
            home_fouls: extractStat(boxscore, home.team.id, [
              "foulsCommitted",
              "fouls",
            ]),
            away_fouls: extractStat(boxscore, away.team.id, [
              "foulsCommitted",
              "fouls",
            ]),
            home_offsides: extractStat(boxscore, home.team.id, "offsides"),
            away_offsides: extractStat(boxscore, away.team.id, "offsides"),
          },
          prediction: {
            match_id: event.id,
            home_win_probability: 0,
            draw_probability: 0,
            away_win_probability: 0,
            over_25_probability: 0,
            under_25_probability: 0,
            predicted_home_goals: 0,
            predicted_away_goals: 0,
            confidence: 0,
            data_sources: ["ESPN"],
            recommended_bet: "N/A",
            over_under_recommendation: "N/A",
            created_at: new Date().toISOString(),
          },
          // Custom property for minute if we want to add it to domain later, or check if Match already supports it.
          // The Match entity doesn't have 'minute', maybe we should add it or use status.
          // For now, let's keep it simple.
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

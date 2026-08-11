import {
  LiveMatchPrediction,
  MatchPrediction,
  Match,
} from "../../domain/entities";
import { fetchESPNLiveMatches } from "../external/espn";
import { API_ENDPOINTS, APP_CONFIG } from "../../config/constants";

import { apiClient } from "./client";

export const liveApi = {
  /**
   * Get all live matches globally
   */
  async getLiveMatches(): Promise<Match[]> {
    const response = await apiClient.get<Match[]>(API_ENDPOINTS.MATCHES_LIVE);
    return response.data;
  },

  /**
   * Get live matches with AI predictions
   * Uses backend first, falls back to ESPN if backend empty/fails
   */
  async getLiveMatchesWithPredictions(
    filterTargetLeagues: boolean = true
  ): Promise<LiveMatchPrediction[]> {
    try {
      // 1. Fetch both sources in parallel
      const [backendResponse, espnMatches] = await Promise.all([
        apiClient
          .get<MatchPrediction[]>(API_ENDPOINTS.MATCHES_LIVE_WITH_PREDICTIONS, {
            params: { filter_target_leagues: filterTargetLeagues },
            timeout: APP_CONFIG.LIVE_API_TIMEOUT,
          })
          .catch(() => ({ data: [] as MatchPrediction[] })), // Soft fail on backend
        fetchESPNLiveMatches(),
      ]);

      const backendMatches = backendResponse.data || [];

      // 2. Map ESPN matches for O(1) lookup (Normalization: lowercase, alphanumeric only)
      const normalize = (name: string): string =>
        name.toLowerCase().replace(/[^a-z0-9]/g, "");

      const espnMap = new Map<string, LiveMatchPrediction>();
      espnMatches.forEach((m) => {
        const key = `${normalize(m.match.home_team.name)}-${normalize(
          m.match.away_team.name
        )}`;
        espnMap.set(key, m);
      });

      // 3. Merge Strategy:
      // - Start with Backend matches (they have rich predictions/stats)
      // - VALIDATE against ESPN (if ESPN has data) to filter zombies
      // - If ESPN is empty, fall back to backend? User said "Only ESPN".
      // - Let's use ESPN as the 'Base' list and enrich with Backend predictions.

      // If ESPN is completely down/empty, should we show nothing?
      // "el boton solamente cuando hay partidos en vivo que viene de la api de ESPN"
      // Implies: If ESPN has nothing, show nothing.
      if (espnMatches.length === 0) {
        // Strict Requirement: Only show matches verified by ESPN as Live ("in" or "ht")
        // "el boton solamente cuando hay partidos en vivo que viene de la api de ESPN"
        return [];
      }

      const mergedMatches: LiveMatchPrediction[] = [];

      // Iterate ESPN matches (The Truth)
      espnMatches.forEach((espnMatch) => {
        // Find matching backend prediction
        const espnHome = normalize(espnMatch.match.home_team.name);
        const espnAway = normalize(espnMatch.match.away_team.name);

        const matchingPrediction = backendMatches.find((bp) => {
          const bpHome = normalize(bp.match.home_team.name);
          const bpAway = normalize(bp.match.away_team.name);
          // Check home vs home AND away vs away
          // OR fuzzy partials? Exact normalized match is safest for now.
          return (
            (bpHome.includes(espnHome) || espnHome.includes(bpHome)) &&
            (bpAway.includes(espnAway) || espnAway.includes(bpAway))
          );
        });

        if (matchingPrediction) {
          // ESPN-first merge: ESPN is the verified live source (a defined
          // value, incl. genuine 0, wins). Backend fills only stats ESPN
          // does not provide (undefined = gap). Minute/status come from
          // ESPN via the base spread; backend-only fields (odds, spi,
          // events) survive it.
          const espn = espnMatch.match;
          const backend = matchingPrediction.match;
          const stat = <K extends keyof Match>(key: K): Match[K] =>
            espn[key] !== undefined ? espn[key] : backend[key];

          mergedMatches.push({
            ...matchingPrediction,
            match: {
              ...espn,
              home_goals: stat("home_goals"),
              away_goals: stat("away_goals"),
              home_corners: stat("home_corners"),
              away_corners: stat("away_corners"),
              home_yellow_cards: stat("home_yellow_cards"),
              away_yellow_cards: stat("away_yellow_cards"),
              home_red_cards: stat("home_red_cards"),
              away_red_cards: stat("away_red_cards"),
              home_total_shots: stat("home_total_shots"),
              away_total_shots: stat("away_total_shots"),
              home_shots_on_target: stat("home_shots_on_target"),
              away_shots_on_target: stat("away_shots_on_target"),
              home_fouls: stat("home_fouls"),
              away_fouls: stat("away_fouls"),
              home_offsides: stat("home_offsides"),
              away_offsides: stat("away_offsides"),
              home_possession: stat("home_possession"),
              away_possession: stat("away_possession"),
              home_odds: backend.home_odds,
              draw_odds: backend.draw_odds,
              away_odds: backend.away_odds,
              home_spi: backend.home_spi,
              away_spi: backend.away_spi,
              events: backend.events,
              match_date: backend.match_date,
            },
            isProcessing: false,
          });
        } else {
          // No prediction, just raw ESPN match
          mergedMatches.push(espnMatch);
        }
      });

      return mergedMatches;
    } catch {
      // Final fallback
      return await fetchESPNLiveMatches();
    }
  },
};

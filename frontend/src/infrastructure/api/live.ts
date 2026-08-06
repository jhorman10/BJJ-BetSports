import { apiClient } from "./client";
import {
  LiveMatchPrediction,
  MatchPrediction,
  Match,
} from "../../domain/entities";
import { fetchESPNLiveMatches } from "../external/espn";
import { API_ENDPOINTS, APP_CONFIG } from "../../config/constants";

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
      const normalize = (name: string) =>
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
      const usedBackendIds = new Set<string>();

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
          usedBackendIds.add(matchingPrediction.match.id);
          // Merge: Use Backend Prediction + ESPN Live Stats (usually fresher minute/score)
          // But Backend might have FotMob stats (corners!)
          // Let's keep Backend Match Data but override status/minute from ESPN
          mergedMatches.push({
            ...matchingPrediction,
            match: {
              ...matchingPrediction.match,
              minute: espnMatch.match.minute, // Trust ESPN time
              status: espnMatch.match.status, // Trust ESPN status
              // Keep FotMob stats from backend if available, else use ESPN
              home_corners:
                matchingPrediction.match.home_corners ??
                espnMatch.match.home_corners,
              away_corners:
                matchingPrediction.match.away_corners ??
                espnMatch.match.away_corners,
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

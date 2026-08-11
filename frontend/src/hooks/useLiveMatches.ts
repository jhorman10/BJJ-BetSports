import { useState, useCallback, useEffect } from "react";

import api from "../services/api";
import { Match, MatchPrediction, Prediction } from "../types";
import { LiveMatchPrediction } from "../domain/entities";
import { fetchESPNLiveMatches } from "../infrastructure/external/espn";

// Local interface until backend adds new fields
export interface LiveMatch {
  id: string;
  home_team:
    | string
    | { id: string; name: string; short_name?: string; logo_url?: string };
  home_short_name?: string;
  away_team:
    | string
    | { id: string; name: string; short_name?: string; logo_url?: string };
  away_short_name?: string;
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
  home_logo_url?: string;
  away_logo_url?: string;
  prediction?: MatchPrediction["prediction"];
}

/**
 * Pure adapter: ESPN domain LiveMatchPrediction → flat LiveMatch.
 *
 * ESPN transport stays nested (match.match.team objects, string minute like
 * "45:00" / "45'") while the UI consumes a flat LiveMatch (numeric minute,
 * flattened league). HT status is preserved; every other state maps to LIVE.
 */
export function toLiveMatch(espn: LiveMatchPrediction): LiveMatch {
  const m = espn.match;
  return {
    id: m.id,
    home_team: m.home_team,
    away_team: m.away_team,
    home_score: m.home_goals ?? 0,
    away_score: m.away_goals ?? 0,
    minute: Number.parseInt((m.minute ?? "0").replace("'", ""), 10) || 0,
    league_id: m.league.id,
    league_name: m.league.name,
    status: m.status === "HT" ? "HT" : "LIVE",
    home_corners: m.home_corners ?? 0,
    away_corners: m.away_corners ?? 0,
    home_yellow_cards: m.home_yellow_cards ?? 0,
    away_yellow_cards: m.away_yellow_cards ?? 0,
    home_red_cards: m.home_red_cards ?? 0,
    away_red_cards: m.away_red_cards ?? 0,
    prediction: espn.prediction,
  };
}

/** Maps a backend Match payload into the flat LiveMatch UI shape. */
const mapBackendMatch = (item: unknown): LiveMatch => {
  const match = item as Match & {
    prediction?: Prediction;
    minute?: number;
  };
  return {
    id: (match.id as string) || "",
    home_team: match.home_team,
    home_short_name: match.home_team?.short_name,
    home_logo_url: match.home_team?.logo_url,
    away_team: match.away_team,
    away_short_name: match.away_team?.short_name,
    away_logo_url: match.away_team?.logo_url,
    home_score: (match.home_goals ?? 0) as number,
    away_score: (match.away_goals ?? 0) as number,
    minute: match.minute || 0,
    league_id: (match.league?.id || "unknown") as string,
    league_name: (match.league?.name || "Liga Desconocida") as string,
    league_flag: (match.league?.flag || undefined) as string | undefined,
    status: (match.status as LiveMatch["status"]) || "LIVE",
    home_corners: (match.home_corners || 0) as number,
    away_corners: (match.away_corners || 0) as number,
    home_yellow_cards: (match.home_yellow_cards || 0) as number,
    away_yellow_cards: (match.away_yellow_cards || 0) as number,
    home_red_cards: (match.home_red_cards || 0) as number,
    away_red_cards: (match.away_red_cards || 0) as number,
    prediction: match.prediction,
  };
};

export const useLiveMatches = (): {
  matches: LiveMatch[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
} => {
  const [matches, setMatches] = useState<LiveMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLiveMatches = useCallback(async () => {
    setLoading(true);
    try {
      let liveMatches: LiveMatch[] = [];

      if (typeof api.getLiveMatches === "function") {
        try {
          const data = await api.getLiveMatches();
          liveMatches = Array.isArray(data) ? data.map(mapBackendMatch) : [];
        } catch {
          // Backend unavailable — fall through to ESPN fallback
        }
      }

      // Fall back to ESPN public API when the backend has no live matches
      if (liveMatches.length === 0) {
        const espnMatches = await fetchESPNLiveMatches();
        liveMatches = espnMatches.map(toLiveMatch);
      }

      setMatches(liveMatches);
    } catch {
      setMatches([]);
    } finally {
      setLoading(false);
      setError(null);
    }
  }, []);

  useEffect(() => {
    fetchLiveMatches();
    const interval = setInterval(fetchLiveMatches, 60000);
    return () => clearInterval(interval);
  }, [fetchLiveMatches]);

  return { matches, loading, error, refresh: fetchLiveMatches };
};

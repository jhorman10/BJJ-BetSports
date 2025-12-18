/**
 * Custom Hooks for Predictions
 *
 * React hooks for fetching and managing prediction data.
 */

import { useState, useEffect, useCallback } from "react";
import { api } from "../services/api";
import {
  LeaguesResponse,
  PredictionsResponse,
  Country,
  League,
} from "../types";

/**
 * Hook for fetching available leagues
 */
export function useLeagues() {
  const [data, setData] = useState<LeaguesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchLeagues = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getLeagues();
      setData(response);
    } catch (err) {
      setError(
        err instanceof Error ? err : new Error("Failed to fetch leagues")
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLeagues();
  }, [fetchLeagues]);

  return {
    data,
    loading,
    error,
    refetch: fetchLeagues,
    countries: data?.countries || [],
    totalLeagues: data?.total_leagues || 0,
  };
}

/**
 * Hook for fetching predictions for a league
 */
export function usePredictions(leagueId: string | null, limit: number = 10) {
  const [data, setData] = useState<PredictionsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchPredictions = useCallback(async () => {
    if (!leagueId) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await api.getPredictions(leagueId, limit);
      setData(response);
    } catch (err) {
      setError(
        err instanceof Error ? err : new Error("Failed to fetch predictions")
      );
    } finally {
      setLoading(false);
    }
  }, [leagueId, limit]);

  useEffect(() => {
    fetchPredictions();
  }, [fetchPredictions]);

  return {
    data,
    loading,
    error,
    refetch: fetchPredictions,
    predictions: data?.predictions || [],
    league: data?.league || null,
  };
}

/**
 * Hook for selected league state
 */
export function useLeagueSelection() {
  const [selectedCountry, setSelectedCountry] = useState<Country | null>(null);
  const [selectedLeague, setSelectedLeague] = useState<League | null>(null);

  const selectCountry = useCallback((country: Country | null) => {
    setSelectedCountry(country);
    setSelectedLeague(null); // Reset league when country changes
  }, []);

  const selectLeague = useCallback((league: League | null) => {
    setSelectedLeague(league);
  }, []);

  const reset = useCallback(() => {
    setSelectedCountry(null);
    setSelectedLeague(null);
  }, []);

  return {
    selectedCountry,
    selectedLeague,
    selectCountry,
    selectLeague,
    reset,
  };
}

/**
 * Custom Hooks for Predictions
 *
 * React hooks for fetching and managing prediction data.
 * Optimized with useMemo and useCallback for performance.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { api } from "../services/api";
import {
  LeaguesResponse,
  PredictionsResponse,
  Country,
  League,
} from "../types";

/**
 * Hook for fetching available leagues
 * Uses memoization to prevent unnecessary re-renders
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
      setError(err instanceof Error ? err : new Error("Error al cargar ligas"));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLeagues();
  }, [fetchLeagues]);

  // Memoize derived values to prevent recalculation on each render
  const countries = useMemo(() => data?.countries || [], [data]);
  const totalLeagues = useMemo(() => data?.total_leagues || 0, [data]);

  return {
    data,
    loading,
    error,
    refetch: fetchLeagues,
    countries,
    totalLeagues,
  };
}

/**
 * Hook for fetching predictions for a league
 * Only fetches when leagueId changes
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
        err instanceof Error ? err : new Error("Error al cargar predicciones")
      );
    } finally {
      setLoading(false);
    }
  }, [leagueId, limit]);

  useEffect(() => {
    fetchPredictions();
  }, [fetchPredictions]);

  // Memoize derived values
  const predictions = useMemo(() => data?.predictions || [], [data]);
  const league = useMemo(() => data?.league || null, [data]);

  return {
    data,
    loading,
    error,
    refetch: fetchPredictions,
    predictions,
    league,
  };
}

/**
 * Hook for selected league state
 * Uses useCallback for stable function references
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

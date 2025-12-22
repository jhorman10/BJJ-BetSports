import { useState, useEffect, useCallback } from "react";
import api from "../services/api";
import { Country, League } from "../types";

export interface UseLeaguesResult {
  countries: Country[];
  selectedCountry: Country | null;
  selectedLeague: League | null;
  loading: boolean;
  error: string | null;
  selectCountry: (country: Country | null) => void;
  selectLeague: (league: League | null) => void;
  refresh: () => Promise<void>;
}

export const useLeagues = (): UseLeaguesResult => {
  const [countries, setCountries] = useState<Country[]>([]);
  const [selectedCountry, setSelectedCountry] = useState<Country | null>(null);
  const [selectedLeague, setSelectedLeague] = useState<League | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchLeagues = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getLeagues();
      setCountries(response.countries);
    } catch (err: any) {
      console.error("Error fetching leagues:", err);
      setError(err.message || "Error cargando las ligas");
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch
  useEffect(() => {
    fetchLeagues();
  }, [fetchLeagues]);

  const selectCountry = useCallback((country: Country | null) => {
    setSelectedCountry(country);
    // Reset league when country changes
    setSelectedLeague(null);
  }, []);

  const selectLeague = useCallback((league: League | null) => {
    setSelectedLeague(league);
  }, []);

  return {
    countries,
    selectedCountry,
    selectedLeague,
    loading,
    error,
    selectCountry,
    selectLeague,
    refresh: fetchLeagues,
  };
};

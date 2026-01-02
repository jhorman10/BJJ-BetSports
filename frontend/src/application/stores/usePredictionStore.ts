import { create } from "zustand";
import { persist } from "zustand/middleware";
import {
  LeaguesResponse,
  MatchPrediction,
  Country,
  League,
} from "../../domain/entities";
import { predictionsApi } from "../../infrastructure/api/predictions";
import { leaguesApi } from "../../infrastructure/api/leagues";
import { useOfflineStore } from "./useOfflineStore";

export type SortOption =
  | "confidence"
  | "date"
  | "home_probability"
  | "away_probability";

interface PredictionState {
  // Data
  leaguesData: LeaguesResponse | null;
  selectedCountry: Country | null;
  selectedLeague: League | null;
  predictions: MatchPrediction[];
  searchMatches: MatchPrediction[]; // For search results

  // UI/Filter State
  searchQuery: string;
  sortBy: SortOption;
  sortDesc: boolean;

  // Status
  leaguesLoading: boolean;
  leaguesError: string | null;
  predictionsLoading: boolean;
  predictionsError: string | null;
  searchLoading: boolean;

  // Training Status
  lastTrainingUpdate: string | null;
  newPredictionsAvailable: boolean;

  // Actions
  fetchLeagues: () => Promise<void>;
  selectCountry: (country: Country | null) => void;
  selectLeague: (league: League | null) => void;
  fetchPredictions: (background?: boolean) => Promise<void>;
  setSearchQuery: (query: string) => void;
  setSortBy: (sort: SortOption) => void;
  resetFilters: () => void;
  performSearch: (query: string) => Promise<void>;
  checkTrainingStatus: () => Promise<void>;
}

export const usePredictionStore = create<PredictionState>()(
  persist(
    (set, get) => ({
      leaguesData: null,
      selectedCountry: null,
      selectedLeague: null,
      predictions: [],
      searchMatches: [],

      searchQuery: "",
      sortBy: "confidence",
      sortDesc: true,

      leaguesLoading: false,
      leaguesError: null,
      predictionsLoading: false,
      predictionsError: null,
      searchLoading: false,

      lastTrainingUpdate: null,
      newPredictionsAvailable: false,

      fetchLeagues: async () => {
        set({ leaguesLoading: true, leaguesError: null });
        try {
          const data = await leaguesApi.getLeagues();
          // Filter out excluded countries
          const excludedCountries = [
            "Turkey",
            "Greece",
            "Scotland",
            "Turquía",
            "Grecia",
            "Escocia",
          ];
          const filteredCountries = data.countries.filter(
            (c) => !excludedCountries.includes(c.name)
          );

          set({
            leaguesData: {
              ...data,
              countries: filteredCountries,
            },
          });

          // Successful fetch means backend is likely available
          useOfflineStore.getState().setBackendAvailable(true);
          useOfflineStore.getState().updateLastSync();
        } catch (err: any) {
          // Check for network error / unreachable backend
          const isNetworkError =
            err.message === "Network Error" || err.code === "ERR_NETWORK";
          if (isNetworkError) {
            useOfflineStore.getState().setBackendAvailable(false);
          }

          // If we have data in cache (persisted), don't show robust error, just a warning maybe?
          // Using current error state to indicate staleness if needed, or keep showing data.
          // We set error string, UI can decide whether to block or show toast.
          set({ leaguesError: err.message || "Error loading leagues" });
        } finally {
          set({ leaguesLoading: false });
        }
      },

      selectCountry: (country) => {
        set({
          selectedCountry: country,
          selectedLeague: null,
          predictions: [], // Clear predictions when country changes
          predictionsError: null,
        });
      },

      selectLeague: (league) => {
        set({
          selectedLeague: league,
          // Don't clear predictions immediately if we want to show cached ones while loading
          // predictions: [],
          predictionsError: null,
          searchQuery: "", // Clear search when changing league
          searchMatches: [],
        });
        if (league) {
          get().fetchPredictions();
        }
      },

      fetchPredictions: async (background = false) => {
        const { selectedLeague, sortBy, sortDesc } = get();
        if (!selectedLeague) {
          set({ predictions: [] });
          return;
        }

        if (!background) {
          set({ predictionsLoading: true, predictionsError: null });
        }

        try {
          const response = await predictionsApi.getPredictions(
            selectedLeague.id,
            30,
            sortBy,
            sortDesc
          );
          set({ predictions: response.predictions });

          // Predictions are fetched fresh each time, no need to persist
          useOfflineStore.getState().setBackendAvailable(true);
          useOfflineStore.getState().updateLastSync();
        } catch (err: any) {
          const isNetworkError =
            err.message === "Network Error" || err.code === "ERR_NETWORK";
          if (isNetworkError) {
            useOfflineStore.getState().setBackendAvailable(false);
          }

          // If persistence worked, 'predictions' still has old data.
          // We set error so UI can show "Offline Mode" badge.
          set({ predictionsError: err.message || "Error loading predictions" });
        } finally {
          if (!background) {
            set({ predictionsLoading: false });
          }
        }
      },

      setSearchQuery: (query) => {
        set({ searchQuery: query });
        if (query.length > 2) {
          get().performSearch(query);
        } else {
          set({ searchMatches: [] });
        }
      },

      performSearch: async (query) => {
        set({ searchLoading: true });
        try {
          const matchPredictions = await predictionsApi.getTeamMatches(query);
          set({ searchMatches: matchPredictions });
          useOfflineStore.getState().setBackendAvailable(true);
        } catch (err: any) {
          const isNetworkError =
            err.message === "Network Error" || err.code === "ERR_NETWORK";
          if (isNetworkError) {
            useOfflineStore.getState().setBackendAvailable(false);
          }
          set({ searchMatches: [] });
        } finally {
          set({ searchLoading: false });
        }
      },

      checkTrainingStatus: async () => {
        try {
          const status = await predictionsApi.getTrainingStatus();
          const { lastTrainingUpdate } = get();

          if (status.last_update && status.last_update !== lastTrainingUpdate) {
            // New update detected
            set({ lastTrainingUpdate: status.last_update });

            // If we had a previous update (not first load), warn user and refresh
            if (lastTrainingUpdate !== null) {
              set({ newPredictionsAvailable: true });
              // Refresh data silently
              get().fetchPredictions(true);
              // Reset notification flag after 5s or let UI handle it
              setTimeout(() => set({ newPredictionsAvailable: false }), 5000);
            }
          }
        } catch (error) {
          // Silent fail on background check
        }
      },

      setSortBy: (sortBy) => {
        set({ sortBy });
        if (get().selectedLeague) {
          get().fetchPredictions();
        }
      },

      resetFilters: () => {
        set({ selectedCountry: null, selectedLeague: null, searchQuery: "" });
      },
    }),
    {
      name: "prediction-storage", // unique name
      // Only persist essential user selections, NOT large data arrays
      partialize: (state) => ({
        // leaguesData is persisted separately via localStorageObserver
        selectedCountry: state.selectedCountry,
        selectedLeague: state.selectedLeague,
        sortBy: state.sortBy,
        sortDesc: state.sortDesc,
        lastTrainingUpdate: state.lastTrainingUpdate,
        // Don't persist predictions, leaguesData, or search results - they're too large
        // and will be fetched fresh when needed
      }),
    }
  )
);

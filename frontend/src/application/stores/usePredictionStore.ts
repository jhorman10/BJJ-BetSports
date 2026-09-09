import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

import {
  LeaguesResponse,
  MatchPrediction,
  Country,
  League,
} from "../../domain/entities";
import { predictionsApi } from "../../infrastructure/api/predictions";
import { leaguesApi } from "../../infrastructure/api/leagues";
import { isNetworkError } from "../../utils/apiErrors";
import { indexedDBStorage } from "../../infrastructure/storage/indexedDBStorage";

import { useOfflineStore } from "./useOfflineStore";
import { useUIStore } from "./useUIStore";

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
  fetchLeagues: (background?: boolean) => Promise<void>;
  selectCountry: (country: Country | null) => void;
  selectLeague: (league: League | null) => void;
  fetchPredictions: (background?: boolean) => Promise<void>;
  setSearchQuery: (query: string) => void;
  setSortBy: (sort: SortOption) => void;
  resetFilters: () => void;
  performSearch: (query: string) => Promise<void>;
  checkTrainingStatus: () => Promise<void>;
}

// Cleanup old localStorage to prevent quota issues on mobile
try {
  if (typeof window !== "undefined") {
    localStorage.removeItem("prediction-storage");
  }
} catch {
  // Silent cleanup fail
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

      fetchLeagues: async (background = false) => {
        if (!background) {
          set({ leaguesLoading: true, leaguesError: null });
        }
        try {
          const sport = useUIStore.getState().selectedSport;
          const data = await leaguesApi.getActiveLeagues(sport);
          const filteredCountries = data.countries.sort((a, b) =>
            a.name.localeCompare(b.name)
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
        } catch (err: unknown) {
          const error =
            err instanceof Error ? err : new Error("Error desconocido");
          // Check for network error / unreachable backend
          const isNetworkErr = isNetworkError(err);
          if (isNetworkErr) {
            useOfflineStore.getState().setBackendAvailable(false);
          }

          // If we have a network error, we don't set leaguesError to avoid showing the red alert box.
          // The global OfflineIndicator will show the orange "Limited Connection" bar.
          set({
            leaguesError: isNetworkErr
              ? null
              : error.message || "Error al cargar las ligas",
          });
        } finally {
          if (!background) {
            set({ leaguesLoading: false });
          }
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
          const sport = useUIStore.getState().selectedSport;
          const response = await predictionsApi.getPredictions(
            selectedLeague.id,
            30,
            sortBy,
            sortDesc,
            sport
          );
          set({ predictions: response.predictions });

          // Predictions are fetched fresh each time, no need to persist
          useOfflineStore.getState().setBackendAvailable(true);
          useOfflineStore.getState().updateLastSync();
        } catch (err: unknown) {
          const error =
            err instanceof Error ? err : new Error("Error desconocido");
          const isNetworkErr = isNetworkError(err);
          if (isNetworkErr) {
            useOfflineStore.getState().setBackendAvailable(false);
          }

          // If we have a network error, we don't set predictionsError to avoid technical alerts.
          set({
            predictionsError: isNetworkErr
              ? null
              : error.message || "Error al cargar las predicciones",
          });
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
        } catch (err: unknown) {
          const isNetworkErr = isNetworkError(err);
          if (isNetworkErr) {
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

          if (
            status.available &&
            status.last_update &&
            status.last_update !== lastTrainingUpdate
          ) {
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
        } catch {
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
      name: "prediction-storage-v2", // unique name
      storage: createJSONStorage(() => indexedDBStorage),
      // Only persist essential user selections, NOT large data arrays
      partialize: (state) => ({
        // leaguesData is persisted separately via localStorageObserver
        selectedCountry: state.selectedCountry,
        selectedLeague: state.selectedLeague,
        sortBy: state.sortBy,
        sortDesc: state.sortDesc,
        lastTrainingUpdate: state.lastTrainingUpdate,
      }),
    }
  )
);

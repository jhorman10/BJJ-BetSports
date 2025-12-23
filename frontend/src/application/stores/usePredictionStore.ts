import { create } from "zustand";
import {
  LeaguesResponse,
  MatchPrediction,
  Country,
  League,
} from "../../domain/entities";
import { predictionsApi } from "../../infrastructure/api/predictions";
import { leaguesApi } from "../../infrastructure/api/leagues";

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

  // Actions
  fetchLeagues: () => Promise<void>;
  selectCountry: (country: Country | null) => void;
  selectLeague: (league: League | null) => void;
  fetchPredictions: () => Promise<void>;
  setSearchQuery: (query: string) => void;
  setSortBy: (sort: SortOption) => void;
  resetFilters: () => void;
  performSearch: (query: string) => Promise<void>;
}

export const usePredictionStore = create<PredictionState>((set, get) => ({
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

  fetchLeagues: async () => {
    set({ leaguesLoading: true, leaguesError: null });
    try {
      const data = await leaguesApi.getLeagues();
      set({ leaguesData: data });
    } catch (err: any) {
      set({ leaguesError: err.message || "Error loading leagues" });
    } finally {
      set({ leaguesLoading: false });
    }
  },

  selectCountry: (country) => {
    set({ selectedCountry: country, selectedLeague: null });
  },

  selectLeague: (league) => {
    set({ selectedLeague: league });
    if (league) {
      get().fetchPredictions();
    }
  },

  fetchPredictions: async () => {
    const { selectedLeague, sortBy, sortDesc } = get();
    if (!selectedLeague) {
      set({ predictions: [] });
      return;
    }

    set({ predictionsLoading: true, predictionsError: null });
    try {
      const response = await predictionsApi.getPredictions(
        selectedLeague.id,
        10,
        sortBy,
        sortDesc
      );
      set({ predictions: response.predictions });
    } catch (err: any) {
      set({ predictionsError: err.message || "Error loading predictions" });
    } finally {
      set({ predictionsLoading: false });
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
      const matches = await predictionsApi.getTeamMatches(query);
      const matchPredictions: MatchPrediction[] = matches.map((m) => ({
        match: m,
        prediction: {
          match_id: m.id,
          home_win_probability: 0,
          draw_probability: 0,
          away_win_probability: 0,
          over_25_probability: 0,
          under_25_probability: 0,
          predicted_home_goals: 0,
          predicted_away_goals: 0,
          confidence: 0,
          data_sources: [],
          recommended_bet: "N/A",
          over_under_recommendation: "N/A",
          created_at: new Date().toISOString(),
        },
      }));
      set({ searchMatches: matchPredictions });
    } catch (err) {
      console.error("Search error", err);
      set({ searchMatches: [] });
    } finally {
      set({ searchLoading: false });
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
}));

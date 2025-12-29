import { create } from "zustand";
import { persist } from "zustand/middleware";
import { LiveMatchPrediction } from "../../domain/entities";
import { liveApi } from "../../infrastructure/api/live";
import { useOfflineStore } from "./useOfflineStore";

interface LiveState {
  matches: LiveMatchPrediction[];
  loading: boolean;
  error: string | null;
  pollingIntervalId: NodeJS.Timeout | null;

  // Actions
  fetchMatches: () => Promise<void>;
  startPolling: (intervalMs?: number) => void;
  stopPolling: () => void;
}

export const useLiveStore = create<LiveState>()(
  persist(
    (set, get) => ({
      matches: [],
      loading: false,
      error: null,
      pollingIntervalId: null,

      fetchMatches: async () => {
        // Only set loading true on first load to avoid flickering
        if (get().matches.length === 0) {
          set({ loading: true });
        }

        try {
          // Intentionally waiting a bit to prevent rapid flickering if called frequently
          // await new Promise(resolve => setTimeout(resolve, 600));
          // Removing artificial delay for store - let UI decide if it needs to wait or show skeleton

          const matches = await liveApi.getLiveMatchesWithPredictions();
          set({ matches, error: null });

          useOfflineStore.getState().setBackendAvailable(true);
          useOfflineStore.getState().updateLastSync();
        } catch (err: any) {
          console.error("Error loading live matches:", err);

          const isNetworkError =
            err.message === "Network Error" || err.code === "ERR_NETWORK";
          if (isNetworkError) {
            useOfflineStore.getState().setBackendAvailable(false);
          }

          // Don't clear matches on error to keep "stale" data visible??
          // Or show empty? Hook showed empty.
          // We'll keep old matches if available, but set error.
          set({ error: err.message || "Error loading live matches" });
        } finally {
          set({ loading: false });
        }
      },

      startPolling: (intervalMs = 60000) => {
        const { stopPolling, fetchMatches } = get();
        stopPolling(); // Ensure no duplicate intervals

        fetchMatches(); // Initial fetch

        const intervalId = setInterval(() => {
          fetchMatches();
        }, intervalMs);

        set({ pollingIntervalId: intervalId });
      },

      stopPolling: () => {
        const { pollingIntervalId } = get();
        if (pollingIntervalId) {
          clearInterval(pollingIntervalId);
          set({ pollingIntervalId: null });
        }
      },
    }),
    {
      name: "live-matches-storage",
      partialize: (state) => ({
        matches: state.matches,
        // Don't persist loading, error, pollingId
      }),
    }
  )
);

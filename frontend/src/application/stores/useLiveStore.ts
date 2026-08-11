import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

import { LiveMatchPrediction } from "../../domain/entities";
import { liveApi } from "../../infrastructure/api/live";
import { isNetworkError } from "../../utils/apiErrors";
import { indexedDBStorage } from "../../infrastructure/storage/indexedDBStorage";

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

// Cleanup old localStorage to prevent quota issues on mobile
try {
  if (typeof window !== "undefined") {
    localStorage.removeItem("live-matches-storage");
  }
} catch {
  // Silent cleanup fail
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
        } catch (err: unknown) {
          const error =
            err instanceof Error ? err : new Error("Error desconocido");
          const isNetworkErr = isNetworkError(err);
          if (isNetworkErr) {
            useOfflineStore.getState().setBackendAvailable(false);
          }

          // Suppress technical error string if it's a network issue
          set({
            error: isNetworkErr
              ? null
              : error.message || "Error al cargar partidos en vivo",
          });
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
      name: "live-matches-storage-v2",
      storage: createJSONStorage(() => indexedDBStorage),
      partialize: (state) => ({
        matches: state.matches,
      }),
    }
  )
);

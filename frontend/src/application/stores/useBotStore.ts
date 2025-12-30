import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { TrainingStatus } from "../../types";
import { api } from "../../services/api";
import { useOfflineStore } from "./useOfflineStore";
import { localStorageObserver } from "../../infrastructure/storage/LocalStorageObserver";
import localforage from "localforage";

// Configure localforage for large dataset storage (IndexedDB)
localforage.config({
  name: "BJJ-BetSports",
  storeName: "bot_storage",
  description: "Storage for AI Training Data & History",
});

interface BotState {
  // Data
  stats: TrainingStatus | null;
  lastUpdate: Date | null;
  lastFetchTimestamp: number | null;

  // UI State
  loading: boolean;
  error: string | null;
  isReconciling: boolean;

  // Actions
  fetchTrainingData: (options?: {
    forceRecalculate?: boolean;
    daysBack?: number;
    startDate?: string;
  }) => Promise<void>;
  updateStats: (stats: TrainingStatus) => void;
  clearCache: () => void;
  reconcile: () => Promise<void>;
}

// Clean up old localStorage to prevent quota errors during migration
try {
  localStorage.removeItem("bot-storage");
} catch (e) {
  console.warn("Failed to clean up old localStorage", e);
}

export const useBotStore = create<BotState>()(
  persist(
    (set, get) => ({
      stats: null,
      lastUpdate: null,
      lastFetchTimestamp: null,
      loading: false,
      error: null,
      isReconciling: false,

      fetchTrainingData: async (options = {}) => {
        const { forceRecalculate = false } = options;

        set({ loading: true, error: null });

        try {
          // Optimization: If we have data from less than 12 hours ago, AND we have the detailed history,
          // don't even check the server-side cache unless forceRecalculate is true.
          const state = get();
          if (
            !forceRecalculate &&
            state.stats &&
            state.lastUpdate &&
            state.stats.match_history
          ) {
            const twelveHoursAgo = Date.now() - 12 * 60 * 60 * 1000;
            if (state.lastUpdate.getTime() > twelveHoursAgo) {
              return; // loading: false will be set in finally
            }
          }

          // First, try to get cached results (instant) from server
          if (!forceRecalculate) {
            try {
              const cachedResponse = await api.get<{
                cached: boolean;
                data: TrainingStatus | null;
                last_update: string | null;
              }>("/train/cached");

              if (cachedResponse.cached && cachedResponse.data) {
                const updateDate = cachedResponse.last_update
                  ? new Date(cachedResponse.last_update)
                  : new Date();

                set({
                  stats: cachedResponse.data,
                  lastUpdate: updateDate,
                  lastFetchTimestamp: Date.now(),
                });

                // Notify observers
                localStorageObserver.persist(
                  "bot-training-data",
                  {
                    stats: cachedResponse.data,
                    timestamp: updateDate.toISOString(),
                  },
                  1000 // 1s debounce for bot data
                );

                // Update offline store
                useOfflineStore.getState().setBackendAvailable(true);
                useOfflineStore.getState().updateLastSync();

                return; // Use cached data
              }
            } catch (cacheError) {
              console.warn(
                "Could not retrieve server-side training cache:",
                cacheError
              );
            }
          }

          // Anti-spam protection: Don't trigger full training if one happened very recently (5 mins)
          if (!forceRecalculate && state.lastFetchTimestamp) {
            const fiveMinutesAgo = Date.now() - 5 * 60 * 1000;
            if (state.lastFetchTimestamp > fiveMinutesAgo && state.stats) {
              return;
            }
          }

          // FALLBACK: Only run full training if absolutely necessary
          // Or if forceRecalculate is true (user clicked the robot icon)
          if (!forceRecalculate && state.stats) {
            // We have some data (even if old), and cache check failed.
            // Better to show old data than to risk a 500/timeout error right now.
            return;
          }

          // No cache or force recalculate - run full training via BACKGROUND JOB (Polling)
          // Avoids CORS/Timeout errors on long-running training (1-2 mins)
          // Note: detailed params (daysBack, startDate) are ignored in this background mode
          // as /train/run-now uses default scheduler settings.

          await api.post("/train/run-now");

          let serverTimestamp: Date | null = null;
          let attempts = 0;
          const maxAttempts = 60; // 5 minutes (5s * 60)
          let newData: TrainingStatus | null = null;

          while (attempts < maxAttempts) {
            await new Promise((resolve) => setTimeout(resolve, 5000));

            try {
              const pollResponse = await api.get<{
                cached: boolean;
                data: TrainingStatus | null;
                last_update: string | null;
              }>("/train/cached");

              if (
                pollResponse.cached &&
                pollResponse.data &&
                pollResponse.last_update
              ) {
                const updateTime = new Date(pollResponse.last_update).getTime();
                // Check if data is fresher than when we started
                const oneMinuteAgo = Date.now() - 60000;

                if (updateTime > oneMinuteAgo) {
                  newData = pollResponse.data;
                  serverTimestamp = new Date(pollResponse.last_update);
                  break;
                }
              }
            } catch (e) {
              console.warn("Polling error (ignoring):", e);
            }
            attempts++;
          }

          if (!newData) {
            throw new Error("Training timed out or failed to produce results.");
          }

          const data = newData;
          const updateDate = serverTimestamp || new Date();

          set({
            stats: data,
            lastUpdate: updateDate,
            lastFetchTimestamp: Date.now(),
            error: null,
          });

          // Notify observers with debouncing
          localStorageObserver.persist(
            "bot-training-data",
            {
              stats: data,
              timestamp: updateDate.toISOString(),
            },
            1000
          );

          // Update offline store
          useOfflineStore.getState().setBackendAvailable(true);
          useOfflineStore.getState().updateLastSync();

          // Show notification if supported
          if (
            "Notification" in window &&
            Notification.permission === "granted"
          ) {
            new Notification("Análisis Completado", {
              body: `ROI: ${data.roi > 0 ? "+" : ""}${data.roi.toFixed(
                1
              )}% | Precisión: ${(data.accuracy * 100).toFixed(1)}%`,
              icon: "/favicon.ico",
            });
          }
        } catch (err: any) {
          // Check for network error
          const isNetworkError =
            err.message === "Network Error" || err.code === "ERR_NETWORK";

          if (isNetworkError) {
            useOfflineStore.getState().setBackendAvailable(false);
          }

          set({
            error: err.message || "Error loading training data",
          });
        } finally {
          set({ loading: false });
        }
      },
      updateStats: (stats) => {
        const now = new Date();
        set({
          stats,
          lastUpdate: now,
          lastFetchTimestamp: Date.now(),
        });

        // Notify observers
        localStorageObserver.persist(
          "bot-training-data",
          {
            stats,
            timestamp: now.toISOString(),
          },
          1000
        );
      },

      clearCache: () => {
        set({
          stats: null,
          lastUpdate: null,
          lastFetchTimestamp: null,
          error: null,
        });
        localStorageObserver.remove("bot-training-data");
        localforage.removeItem("bot-storage");
      },

      reconcile: async () => {
        const state = get();

        // Don't reconcile if we don't have cached data or if we're offline
        if (!state.stats || !useOfflineStore.getState().isBackendAvailable) {
          return;
        }

        set({ isReconciling: true });

        try {
          // Fetch fresh data
          const cachedResponse = await api.get<{
            cached: boolean;
            data: TrainingStatus | null;
            last_update: string | null;
          }>("/train/cached");

          if (cachedResponse.data) {
            const serverUpdateTime = cachedResponse.last_update
              ? new Date(cachedResponse.last_update).getTime()
              : 0;

            const localUpdateTime = state.lastUpdate?.getTime() || 0;

            // If server data is newer, update
            if (serverUpdateTime > localUpdateTime) {
              set({
                stats: cachedResponse.data,
                lastUpdate: new Date(cachedResponse.last_update!),
                lastFetchTimestamp: Date.now(),
              });

              // Persist reconciled data
              localStorageObserver.persist(
                "bot-training-data",
                {
                  stats: cachedResponse.data,
                  timestamp: cachedResponse.last_update,
                },
                0 // No debounce for reconciliation
              );
            }
          }
        } catch (error) {
          // Don't set error state - keep using cached data
        } finally {
          set({ isReconciling: false });
        }
      },
    }),
    {
      name: "bot-storage",
      storage: createJSONStorage(() => ({
        getItem: async (name: string) => {
          const val = await localforage.getItem(name);
          if (!val) return null;
          // handle ancient plain strings vs parsed objects if necessary,
          // but here we trust zustand writes objects.
          // Helper to revive dates if needed, but createJSONStorage usually handles stringifying.
          // localforage stores actual JS objects (IndexedDB), so JSON.parse/stringify
          // might be redundant but createJSONStorage expects string/null mapping.
          // Actually, createJSONStorage + localforage is tricky because localforage is async
          // and createJSONStorage enables async.

          // Wait, standard localforage.getItem() returns the Object if it was setItem() as object.
          // But createJSONStorage expects string.
          // Let's wrap it to return string, or use the object directly if we didn't use createJSONStorage.
          // Best practice with Zustand async:
          return JSON.stringify(val);
        },
        setItem: async (name: string, value: string) => {
          await localforage.setItem(name, JSON.parse(value));
        },
        removeItem: async (name: string) => {
          await localforage.removeItem(name);
        },
      })),
      onRehydrateStorage: () => (state) => {
        // Fix Date deserialization after rehydration
        if (state && state.lastUpdate && typeof state.lastUpdate === "string") {
          state.lastUpdate = new Date(state.lastUpdate);
        }
      },
    }
  )
);

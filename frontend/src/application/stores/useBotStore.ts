import { create } from "zustand";
import { persist } from "zustand/middleware";
import { TrainingStatus } from "../../types";
import { api } from "../../services/api";
import { useOfflineStore } from "./useOfflineStore";
import { localStorageObserver } from "../../infrastructure/storage/LocalStorageObserver";

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
        const { forceRecalculate = false, daysBack = 365, startDate } = options;

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

          // No cache or force recalculate - run full training
          const data = await api.post<TrainingStatus>("/train", {
            league_ids: ["E0", "SP1", "D1", "I1", "F1"],
            days_back: daysBack,
            start_date: startDate,
            reset_weights: false,
          });

          const now = new Date();
          set({
            stats: data,
            lastUpdate: now,
            lastFetchTimestamp: Date.now(),
            error: null,
          });

          // Notify observers with debouncing
          localStorageObserver.persist(
            "bot-training-data",
            {
              stats: data,
              timestamp: now.toISOString(),
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
      partialize: (state) => {
        // Persist essential data. Now that backend truncates history to 500 records,
        // it's safe to persist everything as it won't exceed LocalStorage limits (~5MB).
        if (!state.stats) {
          return {
            stats: null,
            lastUpdate: state.lastUpdate,
            lastFetchTimestamp: state.lastFetchTimestamp,
          };
        }

        return {
          stats: state.stats,
          lastUpdate: state.lastUpdate,
          lastFetchTimestamp: state.lastFetchTimestamp,
        };
      },
      // Fix Date deserialization from localStorage
      storage: {
        getItem: (name) => {
          const str = localStorage.getItem(name);
          if (!str) return null;

          const { state } = JSON.parse(str);
          // Convert lastUpdate string back to Date
          if (state.lastUpdate) {
            state.lastUpdate = new Date(state.lastUpdate);
          }
          return { state };
        },
        setItem: (name, value) => {
          localStorage.setItem(name, JSON.stringify(value));
        },
        removeItem: (name) => {
          localStorage.removeItem(name);
        },
      },
    }
  )
);

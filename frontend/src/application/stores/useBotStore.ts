import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import {
  TrainingStatus,
  TrainingProcessStatus,
  TrainingProgressStatus,
} from "../../types";
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

  // New Status State
  trainingStatus: TrainingProcessStatus;
  trainingMessage: string;
  hasResult: boolean;

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
  pollTrainingStatus: () => Promise<void>;
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
      trainingStatus: "IDLE",
      trainingMessage: "El bot está listo",
      hasResult: false,
      loading: false,
      error: null,
      isReconciling: false,

      fetchTrainingData: async (options = {}) => {
        const { forceRecalculate = false } = options;
        const state = get();

        // If we already have data and it's fresh, don't re-fetch unless forced
        if (!forceRecalculate && state.stats && state.lastUpdate) {
          const twelveHoursAgo = Date.now() - 12 * 60 * 60 * 1000;
          if (
            state.lastUpdate.getTime() > twelveHoursAgo &&
            state.stats.match_history
          ) {
            return;
          }
        }

        set({ loading: true, error: null });

        try {
          // 1. First check current status and if a result exists on server
          const statusRes = await api.get<TrainingProgressStatus>(
            "/train/status"
          );

          set({
            trainingStatus: statusRes.status,
            trainingMessage: statusRes.message,
            hasResult: statusRes.has_result,
          });

          // 2. If we have a result and it's what we need, use it immediately
          if (statusRes.has_result && statusRes.result && !forceRecalculate) {
            const updateDate = statusRes.last_update
              ? new Date(statusRes.last_update)
              : new Date();

            set({
              stats: statusRes.result,
              lastUpdate: updateDate,
              lastFetchTimestamp: Date.now(),
              loading: false,
            });

            // Persist & Notify
            localStorageObserver.persist(
              "bot-training-data",
              {
                stats: statusRes.result,
                timestamp: updateDate.toISOString(),
              },
              1000
            );

            useOfflineStore.getState().setBackendAvailable(true);
            return;
          }

          // 3. If training is already IN_PROGRESS, we just poll
          if (statusRes.status === "IN_PROGRESS") {
            await get().pollTrainingStatus();
            return;
          }

          // 4. If we need to trigger a new training
          if (forceRecalculate || !statusRes.has_result) {
            set({
              trainingStatus: "IN_PROGRESS",
              trainingMessage: "Iniciando entrenamiento...",
            });
            await api.post("/train/run-now");
            await get().pollTrainingStatus();
          }
        } catch (err: any) {
          console.error("Error fetching training data:", err);
          set({
            error: err.message || "Error al cargar los datos de entrenamiento",
            trainingStatus: "ERROR",
            trainingMessage: "Error en la conexión",
          });
        } finally {
          set({ loading: false });
        }
      },

      // Separate polling function to avoid nesting
      pollTrainingStatus: async () => {
        let attempts = 0;
        const maxAttempts = 120; // 10 minutes (5s * 120)
        const pollInterval = 5000;

        while (attempts < maxAttempts) {
          try {
            const statusRes = await api.get<TrainingProgressStatus>(
              "/train/status"
            );

            set({
              trainingStatus: statusRes.status,
              trainingMessage: statusRes.message,
              hasResult: statusRes.has_result,
            });

            if (statusRes.status === "COMPLETED" && statusRes.result) {
              const updateDate = statusRes.last_update
                ? new Date(statusRes.last_update)
                : new Date();
              set({
                stats: statusRes.result,
                lastUpdate: updateDate,
                lastFetchTimestamp: Date.now(),
                error: null,
              });

              localStorageObserver.persist(
                "bot-training-data",
                {
                  stats: statusRes.result,
                  timestamp: updateDate.toISOString(),
                },
                1000
              );

              return;
            }

            if (statusRes.status === "ERROR") {
              throw new Error(
                statusRes.message || "El entrenamiento falló en el servidor"
              );
            }
          } catch (e: any) {
            console.warn("Poll attempt failed:", e);
            if (attempts > 10) {
              // Only show error after repeated failures
              set({ error: "Error de conexión al monitorear entrenamiento" });
            }
          }

          await new Promise((resolve) => setTimeout(resolve, pollInterval));
          attempts++;
        }

        throw new Error(
          "Tiempo agotado: El entrenamiento está tardando demasiado"
        );
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

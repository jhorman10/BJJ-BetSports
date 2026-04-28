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
import { indexedDBStorage } from "../../infrastructure/storage/indexedDBStorage";
import localforage from "localforage";

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
  isTrainingServiceUnavailable: boolean;

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
} catch {
  // Silent cleanup
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
      isTrainingServiceUnavailable: false,

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
            isTrainingServiceUnavailable: false,
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
              error: null,
              isTrainingServiceUnavailable: false,
            });

            useOfflineStore.getState().setBackendAvailable(true);
            return;
          }

          // 3. If training is already IN_PROGRESS, we just poll
          if (statusRes.status === "IN_PROGRESS") {
            await get().pollTrainingStatus();
            return;
          }

          // 4. Only trigger a new training run when the user explicitly requests it.
          if (forceRecalculate) {
            set({
              trainingStatus: "IN_PROGRESS",
              trainingMessage: "Iniciando entrenamiento...",
            });
            await api.post("/train/run-now");
            await get().pollTrainingStatus();
          }
        } catch (err: unknown) {
          const error =
            err instanceof Error ? err : new Error("Error desconocido");
          const statusCode = (err as { response?: { status?: number } })?.response
            ?.status;
          const isNetworkError =
            error.message === "Network Error" ||
            (err as { code?: string })?.code === "ERR_NETWORK" ||
            (err as { code?: string })?.code === "ECONNABORTED";
          const isTrainingServiceUnavailable = statusCode === 503;

          if (isNetworkError) {
            useOfflineStore.getState().setBackendAvailable(false);
          }

          set({
            error: isNetworkError
              ? null
              : isTrainingServiceUnavailable
              ? "El servicio de entrenamiento no esta disponible en este momento. Intenta de nuevo en unos minutos."
              : error.message || "Error al cargar los datos de entrenamiento",
            trainingStatus:
              isNetworkError || isTrainingServiceUnavailable ? "IDLE" : "ERROR",
            trainingMessage: isNetworkError
              ? "Buscando servidor..."
              : isTrainingServiceUnavailable
              ? "Servicio de entrenamiento temporalmente no disponible"
              : "Error en la conexión",
            isTrainingServiceUnavailable,
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
                isTrainingServiceUnavailable: false,
              });

              return;
            }

            if (statusRes.status === "ERROR") {
              throw new Error(
                statusRes.message || "El entrenamiento falló en el servidor"
              );
            }
          } catch {
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
          error: null,
          isTrainingServiceUnavailable: false,
        });
      },

      clearCache: () => {
        set({
          stats: null,
          lastUpdate: null,
          lastFetchTimestamp: null,
          error: null,
          isTrainingServiceUnavailable: false,
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
            }
          }
        } catch {
          // Don't set error state - keep using cached data
        } finally {
          set({ isReconciling: false });
        }
      },
    }),
    {
      name: "bot-storage",
      storage: createJSONStorage(() => indexedDBStorage),
      onRehydrateStorage: () => (state) => {
        // Fix Date deserialization after rehydration
        if (state && state.lastUpdate && typeof state.lastUpdate === "string") {
          state.lastUpdate = new Date(state.lastUpdate);
        }
      },
    }
  )
);

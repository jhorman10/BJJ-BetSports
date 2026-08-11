import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import localforage from "localforage";

import {
  TrainingStatus,
  TrainingProcessStatus,
  TrainingLatestResult,
  TrainingJobSummary,
} from "../../types";
import { api } from "../../services/api";
import { isNetworkError } from "../../utils/apiErrors";
import { localStorageObserver } from "../../infrastructure/storage/LocalStorageObserver";
import { indexedDBStorage } from "../../infrastructure/storage/indexedDBStorage";

import { useOfflineStore } from "./useOfflineStore";

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
  pollTrainingStatus: (jobId?: string) => Promise<void>;
  updateStats: (stats: TrainingStatus) => void;
  clearCache: () => void;
  reconcile: () => Promise<void>;
}

const ACTIVE_JOB_STATUSES = new Set([
  "QUEUED",
  "VALIDATING",
  "PREPARING_DATA",
  "RUNNING",
]);

const DEFAULT_TRAINING_REQUEST = {
  recipe_id: "bootstrap-baseline-model",
  name: "Bootstrap manual training",
  model_key: "baseline-model",
  dataset_profile: "default",
  league_ids: ["E0"],
  days_back: 550,
  feature_profile: "default",
  executor_target: "default",
};

const mapJobStatus = (
  job: TrainingJobSummary | null
): Pick<BotState, "trainingStatus" | "trainingMessage" | "hasResult"> => {
  if (!job) {
    return {
      trainingStatus: "IDLE",
      trainingMessage: "El bot está listo",
      hasResult: false,
    };
  }

  if (ACTIVE_JOB_STATUSES.has(job.status)) {
    return {
      trainingStatus: "IN_PROGRESS",
      trainingMessage: job.status_message || "Entrenamiento en progreso",
      hasResult: false,
    };
  }

  if (job.status === "FAILED" || job.status === "CANCELED") {
    return {
      trainingStatus: "ERROR",
      trainingMessage: job.status_message || "El entrenamiento falló",
      hasResult: false,
    };
  }

  return {
    trainingStatus: "COMPLETED",
    trainingMessage: job.status_message || "Entrenamiento completado",
    hasResult: true,
  };
};

const getActiveJob = (jobs: TrainingJobSummary[]): TrainingJobSummary | null =>
  jobs.find((job) => ACTIVE_JOB_STATUSES.has(job.status)) ?? null;

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
          const [latestResult, jobsResponse] = await Promise.all([
            api.get<TrainingLatestResult>("/training/results/latest"),
            api.get<{ jobs: TrainingJobSummary[] }>("/training/jobs"),
          ]);
          const activeJob = getActiveJob(jobsResponse.jobs);

          if (latestResult.available && latestResult.data) {
            const updateDate = latestResult.last_update
              ? new Date(latestResult.last_update)
              : new Date();
            set({
              stats: latestResult.data,
              lastUpdate: updateDate,
              lastFetchTimestamp: Date.now(),
              error: null,
              isTrainingServiceUnavailable: false,
            });
          }

          set({
            ...mapJobStatus(activeJob),
            hasResult: latestResult.available,
            isTrainingServiceUnavailable: false,
          });

          useOfflineStore.getState().setBackendAvailable(true);
          useOfflineStore.getState().updateLastSync();

          if (activeJob) {
            await get().pollTrainingStatus(activeJob.job_id);
            return;
          }

          if (forceRecalculate) {
            set({
              trainingStatus: "IN_PROGRESS",
              trainingMessage: "Iniciando entrenamiento...",
            });

            const createdJob = await api.post<{ job_id: string }>(
              "/training/jobs",
              DEFAULT_TRAINING_REQUEST
            );
            await get().pollTrainingStatus(createdJob.job_id);
            return;
          }

          if (latestResult.available) {
            set({
              trainingStatus: "COMPLETED",
              trainingMessage: "Último entrenamiento disponible",
              hasResult: true,
            });
          }
        } catch (err: unknown) {
          const error =
            err instanceof Error ? err : new Error("Error desconocido");
          const statusCode = (err as { response?: { status?: number } })?.response
            ?.status;
          const isNetworkErr = isNetworkError(err);
          const isTrainingServiceUnavailable = statusCode === 503;

          if (isNetworkErr) {
            useOfflineStore.getState().setBackendAvailable(false);
          }

          set({
            error: isNetworkErr
              ? null
              : isTrainingServiceUnavailable
              ? "El servicio de entrenamiento no esta disponible en este momento. Intenta de nuevo en unos minutos."
              : error.message || "Error al cargar los datos de entrenamiento",
            trainingStatus:
              isNetworkErr || isTrainingServiceUnavailable ? "IDLE" : "ERROR",
            trainingMessage: isNetworkErr
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
      pollTrainingStatus: async (jobId?: string) => {
        let attempts = 0;
        const maxAttempts = 120; // 10 minutes (5s * 120)
        const pollInterval = 5000;
        let resolvedJobId = jobId;

        if (!resolvedJobId) {
          const jobsResponse = await api.get<{ jobs: TrainingJobSummary[] }>(
            "/training/jobs"
          );
          resolvedJobId = getActiveJob(jobsResponse.jobs)?.job_id;
        }

        if (!resolvedJobId) {
          return;
        }

        while (attempts < maxAttempts) {
          try {
            const statusRes = await api.get<TrainingJobSummary>(
              `/training/jobs/${resolvedJobId}`
            );
            const mappedStatus = mapJobStatus(statusRes);

            set({
              trainingStatus: mappedStatus.trainingStatus,
              trainingMessage: mappedStatus.trainingMessage,
              hasResult: mappedStatus.hasResult,
            });

            if (statusRes.status === "COMPLETED") {
              const latestResult = await api.get<TrainingLatestResult>(
                "/training/results/latest"
              );
              const updateDate = latestResult.last_update
                ? new Date(latestResult.last_update)
                : new Date();

              if (latestResult.data) {
                set({
                  stats: latestResult.data,
                  lastUpdate: updateDate,
                  lastFetchTimestamp: Date.now(),
                  error: null,
                  isTrainingServiceUnavailable: false,
                  hasResult: latestResult.available,
                });
              }

              return;
            }

            if (statusRes.status === "FAILED" || statusRes.status === "CANCELED") {
              throw new Error(
                statusRes.status_message || "El entrenamiento falló en el servidor"
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
          const latestResult = await api.get<TrainingLatestResult>(
            "/training/results/latest"
          );

          if (latestResult.data) {
            const serverUpdateTime = latestResult.last_update
              ? new Date(latestResult.last_update).getTime()
              : 0;

            const localUpdateTime = state.lastUpdate?.getTime() || 0;

            // If server data is newer, update
            if (serverUpdateTime > localUpdateTime) {
              set({
                stats: latestResult.data,
                lastUpdate: new Date(latestResult.last_update!),
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

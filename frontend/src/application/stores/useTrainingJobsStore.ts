import { create } from "zustand";

import {
  TrainingCapabilities,
  TrainingJobCreateRequest,
  TrainingJobEvent,
  TrainingJobRecipeSnapshot,
  TrainingJobSummary,
} from "../../types";
import { api } from "../../services/api";

type TrainingJobDetailsResponse = {
  job_id: string;
  status: TrainingJobSummary["status"];
  status_message: string;
  progress_percent: number;
  phase: NonNullable<TrainingJobSummary["phase"]>;
  executor_type: string | null;
  executor_run_id: string | null;
  queued_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  cancel_requested_at: string | null;
  error_code: string | null;
  error_message: string | null;
  result_summary: Record<string, unknown>;
  artifact_ids: string[];
  audit_trail: Record<string, unknown>[];
  recipe_snapshot: {
    executor_target: string;
    model_key: string;
    [key: string]: unknown;
  };
};

type TrainingJobEventsResponse = {
  job_id: string;
  events: TrainingJobEvent[];
};

type TrainingModelsResponse = {
  models: TrainingCapabilities["models"];
};

type TrainingJobsState = {
  jobs: TrainingJobSummary[];
  capabilities: TrainingCapabilities | null;
  selectedJobId: string | null;
  selectedJobEvents: TrainingJobEvent[];
  isLoading: boolean;
  error: string | null;
  loadCapabilities: () => Promise<TrainingCapabilities>;
  createJob: (request: TrainingJobCreateRequest) => Promise<TrainingJobSummary>;
  loadJobs: () => Promise<void>;
  refreshSelectedJob: () => Promise<void>;
  hydrateJobs: (jobs: TrainingJobSummary[]) => void;
  setCapabilities: (capabilities: TrainingCapabilities | null) => void;
  setSelectedJobId: (jobId: string | null) => void;
  setLoading: (isLoading: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
};

const initialState = {
  jobs: [] as TrainingJobSummary[],
  capabilities: null as TrainingCapabilities | null,
  selectedJobId: null as string | null,
  selectedJobEvents: [] as TrainingJobEvent[],
  isLoading: false,
  error: null as string | null,
};

const normalizeJob = (
  job: TrainingJobSummary | TrainingJobDetailsResponse
): TrainingJobSummary => {
  const recipe = job.recipe_snapshot as Partial<TrainingJobRecipeSnapshot> | undefined;

  // Determine created_at: Summary has it, Details has queued_at
  const created_at = "created_at" in job ? job.created_at : job.queued_at ?? null;

  // Determine updated_at: Summary has updated_at, Details has finished_at/started_at
  const updated_at = "updated_at" in job
    ? job.updated_at
    : job.finished_at ?? job.started_at ?? null;

  return {
    job_id: job.job_id,
    status: job.status,
    status_message: job.status_message,
    progress_percent: job.progress_percent,
    model_key: recipe?.model_key ?? null,
    executor_target: recipe?.executor_target ?? null,
    created_at,
    updated_at,
    phase: job.phase,
    executor_type: job.executor_type ?? null,
    executor_run_id: job.executor_run_id ?? null,
    recipe_snapshot: recipe,
    result_summary: job.result_summary ?? {},
    artifact_ids: job.artifact_ids ?? [],
    audit_trail: job.audit_trail ?? [],
    started_at: job.started_at ?? null,
    finished_at: job.finished_at ?? null,
    cancel_requested_at: job.cancel_requested_at ?? null,
    error_code: job.error_code ?? null,
    error_message: job.error_message ?? null,
  };
};

const upsertJobs = (
  jobs: TrainingJobSummary[],
  incomingJob: TrainingJobSummary
): TrainingJobSummary[] => {
  const nextJobs = jobs.filter((job) => job.job_id !== incomingJob.job_id);
  return [incomingJob, ...nextJobs];
};

export const useTrainingJobsStore = create<TrainingJobsState>((set, get) => ({
  ...initialState,
  loadCapabilities: async () => {
    set({ isLoading: true, error: null });
    try {
      const [capabilities, modelsResponse] = await Promise.all([
        api.get<TrainingCapabilities>("/training/capabilities"),
        api.get<TrainingModelsResponse>("/training/models"),
      ]);
      const normalizedCapabilities = {
        ...capabilities,
        models: modelsResponse.models,
      };
      set({ capabilities: normalizedCapabilities, isLoading: false, error: null });
      return normalizedCapabilities;
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "No se pudo cargar el catalogo de entrenamiento";
      set({ isLoading: false, error: message });
      throw error;
    }
  },
  createJob: async (request) => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.post<TrainingJobDetailsResponse>(
        "/training/jobs",
        request
      );
      const job = normalizeJob(response);
      set((state) => ({
        jobs: upsertJobs(state.jobs, job),
        selectedJobId: job.job_id,
        selectedJobEvents: [],
        isLoading: false,
        error: null,
      }));
      return job;
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "No se pudo crear el job";
      set({ isLoading: false, error: message });
      throw error;
    }
  },
  loadJobs: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await api.get<{ jobs: TrainingJobSummary[] }>(
        "/training/jobs"
      );
      const normalizedJobs = response.jobs.map(normalizeJob);
      set((state) => ({
        jobs: normalizedJobs,
        selectedJobId:
          state.selectedJobId ?? normalizedJobs[0]?.job_id ?? null,
        isLoading: false,
        error: null,
      }));
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "No se pudo cargar el historial";
      set({ isLoading: false, error: message });
      throw error;
    }
  },
  refreshSelectedJob: async () => {
    const selectedJobId = get().selectedJobId;
    if (!selectedJobId) {
      return;
    }

    set({ isLoading: true, error: null });
    try {
      const [jobResponse, eventsResponse] = await Promise.all([
        api.get<TrainingJobDetailsResponse>(`/training/jobs/${selectedJobId}`),
        api.get<TrainingJobEventsResponse>(
          `/training/jobs/${selectedJobId}/events`
        ),
      ]);
      const job = normalizeJob(jobResponse);
      set((state) => ({
        jobs: upsertJobs(state.jobs, job),
        selectedJobEvents: eventsResponse.events,
        isLoading: false,
        error: null,
      }));
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "No se pudo refrescar el job";
      set({ isLoading: false, error: message });
      throw error;
    }
  },
  hydrateJobs: (jobs) => set({ jobs: jobs.map(normalizeJob), error: null }),
  setCapabilities: (capabilities) => set({ capabilities }),
  setSelectedJobId: (selectedJobId) =>
    set({ selectedJobId, selectedJobEvents: [] }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),
  reset: () => set(initialState),
}));
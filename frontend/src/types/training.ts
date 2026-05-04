import type { TrainingStatus } from "./components";

export type TrainingJobStatus =
  | "QUEUED"
  | "VALIDATING"
  | "PREPARING_DATA"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELED";

export type TrainingJobPhase =
  | "REQUESTED"
  | "VALIDATION"
  | "DATA_PREPARATION"
  | "TRAINING"
  | "EVALUATION"
  | "PUBLISHING"
  | "FINISHED";

export interface TrainingJobRecipeSnapshot {
  recipe_id: string;
  name: string;
  model_key: string;
  dataset_profile: string;
  league_ids: string[];
  days_back: number;
  feature_profile: string;
  hyperparameter_profile: string;
  executor_target: string;
  publish_strategy: string;
  requested_by: string | null;
  requested_at: string | null;
  description: string | null;
}

export interface TrainingJobCreateRequest {
  recipe_id: string;
  name: string;
  model_key: string;
  dataset_profile: string;
  league_ids: string[];
  days_back: number;
  feature_profile?: string;
  hyperparameter_profile?: string;
  executor_target?: string;
  publish_strategy?: string;
  description?: string | null;
}

export interface TrainingJobSummary {
  job_id: string;
  status: TrainingJobStatus;
  status_message: string;
  progress_percent: number;
  model_key: string | null;
  executor_target: string | null;
  created_at: string | null;
  updated_at: string | null;
  phase?: TrainingJobPhase;
  executor_type?: string | null;
  executor_run_id?: string | null;
  recipe_snapshot?: TrainingJobRecipeSnapshot;
  result_summary?: Record<string, unknown>;
  artifact_ids?: string[];
  audit_trail?: Record<string, unknown>[];
  started_at?: string | null;
  finished_at?: string | null;
  cancel_requested_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
}

export interface TrainingJobEvent {
  event_id: string;
  job_id: string;
  event_type: string;
  message: string;
  phase: TrainingJobPhase | null;
  progress_percent: number | null;
  payload: Record<string, unknown>;
  created_at: string | null;
}

export interface TrainingOption {
  key: string;
  label: string;
  description?: string;
}

export interface TrainingModelOption extends TrainingOption {
  supported_feature_profiles: string[];
  supported_dataset_profiles: string[];
  supported_executor_targets: string[];
  supported_league_ids: string[];
  supported_days_back: number[];
  default_executor_target: string | null;
}

export interface TrainingExecutorOption extends TrainingOption {
  available: boolean;
  supports_cancel: boolean;
  supports_logs: boolean;
}

export interface TrainingCapabilityReason {
  code: string;
  message: string;
}

export interface TrainingCapabilities {
  available: boolean;
  models: TrainingModelOption[];
  executors: TrainingExecutorOption[];
  dataset_profiles: TrainingOption[];
  feature_profiles: TrainingOption[];
  league_options: TrainingOption[];
  days_back_options: number[];
  reasons: TrainingCapabilityReason[];
}

export interface TrainingLatestResult {
  available: boolean;
  data: TrainingStatus | null;
  last_update: string | null;
}
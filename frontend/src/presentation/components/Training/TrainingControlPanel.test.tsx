import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

vi.mock("../../../services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { api } from "../../../services/api";
import { useTrainingJobsStore } from "../../../application/stores/useTrainingJobsStore";

import TrainingControlPanel from "./TrainingControlPanel";

const mockedGet = vi.mocked(api.get);
const mockedPost = vi.mocked(api.post);

describe("TrainingControlPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useTrainingJobsStore.getState().reset();
  });

  it("loads capabilities and creates a job from the selected options", async () => {
    mockedGet.mockResolvedValue({
      available: true,
      models: [
        {
          key: "baseline-model",
          label: "Baseline Model",
          description: "Default model",
          supported_feature_profiles: ["default"],
          supported_dataset_profiles: ["default"],
          supported_executor_targets: ["default"],
          supported_league_ids: ["E0", "SP1"],
          supported_days_back: [30, 90],
          default_executor_target: "default",
        },
      ],
      executors: [
        {
          key: "default",
          label: "Default Executor",
          description: "Local passive executor",
          available: true,
          supports_cancel: false,
          supports_logs: false,
        },
      ],
      dataset_profiles: [{ key: "default", label: "Default" }],
      feature_profiles: [{ key: "default", label: "Default" }],
      league_options: [
        { key: "E0", label: "Premier League" },
        { key: "SP1", label: "La Liga" },
      ],
      days_back_options: [30, 90],
      reasons: [],
    });
    mockedPost.mockResolvedValue({
      job_id: "job-123",
      status: "QUEUED",
      status_message: "Queued for executor dispatch",
      progress_percent: 0,
      phase: "REQUESTED",
      executor_type: "passive-executor",
      executor_run_id: "run::job-123",
      queued_at: new Date().toISOString(),
      started_at: null,
      finished_at: null,
      cancel_requested_at: null,
      error_code: null,
      error_message: null,
      result_summary: {},
      artifact_ids: [],
      audit_trail: [],
      recipe_snapshot: {
        recipe_id: "manual-baseline-model",
        name: "Manual training",
        model_key: "baseline-model",
        dataset_profile: "default",
        league_ids: ["SP1"],
        days_back: 90,
        feature_profile: "default",
        hyperparameter_profile: "default",
        executor_target: "default",
        publish_strategy: "manual",
        requested_by: "test-key",
        requested_at: new Date().toISOString(),
        description: null,
      },
    });

    render(<TrainingControlPanel />);

    await waitFor(() => {
      expect(mockedGet).toHaveBeenCalledWith("/training/capabilities");
    });

    fireEvent.change(screen.getByLabelText(/Liga/i), {
      target: { value: "SP1" },
    });
    fireEvent.change(screen.getByLabelText(/Ventana/i), {
      target: { value: "90" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Crear entrenamiento/i }));

    await waitFor(() => {
      expect(mockedPost).toHaveBeenCalledWith("/training/jobs", {
        recipe_id: "manual-baseline-model",
        name: "Manual training",
        model_key: "baseline-model",
        dataset_profile: "default",
        league_ids: ["SP1"],
        days_back: 90,
        feature_profile: "default",
        executor_target: "default",
      });
    });
  });

  it("shows actionable capability reasons when training is unavailable", async () => {
    mockedGet.mockResolvedValue({
      available: false,
      models: [],
      executors: [],
      dataset_profiles: [],
      feature_profiles: [],
      league_options: [],
      days_back_options: [],
      reasons: [
        {
          code: "executor_unavailable",
          message: "No hay ejecutores disponibles en este momento.",
        },
      ],
    });

    render(<TrainingControlPanel />);

    expect(
      await screen.findByText(/No hay ejecutores disponibles en este momento/i)
    ).toBeInTheDocument();
  });
});
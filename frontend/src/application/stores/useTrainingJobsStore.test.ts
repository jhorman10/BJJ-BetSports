import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

import { api } from "../../services/api";
import { useTrainingJobsStore } from "./useTrainingJobsStore";

const mockedGet = vi.mocked(api.get);
const mockedPost = vi.mocked(api.post);

describe("useTrainingJobsStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useTrainingJobsStore.getState().reset();
  });

  it("creates a training job and selects it for polling", async () => {
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
        recipe_id: "recipe-001",
        name: "Manual training",
        model_key: "baseline-model",
        dataset_profile: "default",
        league_ids: ["E0"],
        days_back: 30,
        feature_profile: "default",
        hyperparameter_profile: "default",
        executor_target: "default",
        publish_strategy: "manual",
        requested_by: "test-key",
        requested_at: new Date().toISOString(),
        description: null,
      },
    });

    await useTrainingJobsStore.getState().createJob({
      recipe_id: "recipe-001",
      name: "Manual training",
      model_key: "baseline-model",
      dataset_profile: "default",
      league_ids: ["E0"],
      days_back: 30,
    });

    const state = useTrainingJobsStore.getState();

    expect(mockedPost).toHaveBeenCalledWith("/training/jobs", {
      recipe_id: "recipe-001",
      name: "Manual training",
      model_key: "baseline-model",
      dataset_profile: "default",
      league_ids: ["E0"],
      days_back: 30,
    });
    expect(state.selectedJobId).toBe("job-123");
    expect(state.jobs[0]?.job_id).toBe("job-123");
  });

  it("polls the selected job and refreshes its timeline", async () => {
    useTrainingJobsStore.setState({
      jobs: [
        {
          job_id: "job-123",
          status: "QUEUED",
          status_message: "Queued for executor dispatch",
          progress_percent: 0,
          model_key: "baseline-model",
          executor_target: "default",
          created_at: null,
          updated_at: null,
        },
      ],
      selectedJobId: "job-123",
    });

    mockedGet
      .mockResolvedValueOnce({
        job_id: "job-123",
        status: "RUNNING",
        status_message: "Training in progress",
        progress_percent: 45,
        phase: "TRAINING",
        executor_type: "passive-executor",
        executor_run_id: "run::job-123",
        queued_at: new Date().toISOString(),
        started_at: new Date().toISOString(),
        finished_at: null,
        cancel_requested_at: null,
        error_code: null,
        error_message: null,
        result_summary: {},
        artifact_ids: [],
        audit_trail: [],
        recipe_snapshot: {
          recipe_id: "recipe-001",
          name: "Manual training",
          model_key: "baseline-model",
          dataset_profile: "default",
          league_ids: ["E0"],
          days_back: 30,
          feature_profile: "default",
          hyperparameter_profile: "default",
          executor_target: "default",
          publish_strategy: "manual",
          requested_by: "test-key",
          requested_at: new Date().toISOString(),
          description: null,
        },
      })
      .mockResolvedValueOnce({
        job_id: "job-123",
        events: [
          {
            event_id: "event-1",
            job_id: "job-123",
            event_type: "training.job.created",
            message: "Training job created",
            phase: "REQUESTED",
            progress_percent: 0,
            payload: {},
            created_at: new Date().toISOString(),
          },
        ],
      });

    await useTrainingJobsStore.getState().refreshSelectedJob();

    const state = useTrainingJobsStore.getState();

    expect(mockedGet).toHaveBeenNthCalledWith(1, "/training/jobs/job-123");
    expect(mockedGet).toHaveBeenNthCalledWith(
      2,
      "/training/jobs/job-123/events"
    );
    expect(state.jobs[0]?.status).toBe("RUNNING");
    expect(state.selectedJobEvents).toHaveLength(1);
  });
});
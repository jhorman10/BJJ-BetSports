import { describe, expect, it } from "vitest";

import { API_ENDPOINTS, APP_CONFIG } from "./constants";

describe("API_ENDPOINTS", () => {
  it("routes training triggers to the run-now endpoint", () => {
    expect(API_ENDPOINTS.TRAIN).toBe("/api/v1/train/run-now");
  });

  it("no longer exposes dead parleys/top-ml-picks endpoints", () => {
    expect("PARLEYS" in API_ENDPOINTS).toBe(false);
    expect("TOP_ML_PICKS" in API_ENDPOINTS).toBe(false);
  });
});

describe("APP_CONFIG timeout/limit policy", () => {
  it("centralizes the normalized live timeout at 30s", () => {
    expect(APP_CONFIG.LIVE_API_TIMEOUT).toBe(30000);
  });

  it("keeps suggested-picks at 90s", () => {
    expect(APP_CONFIG.SUGGESTED_PICKS_TIMEOUT).toBe(90000);
  });

  it("keeps training at 5 minutes", () => {
    expect(APP_CONFIG.TRAINING_TIMEOUT).toBe(300000);
  });

  it("centralizes the predictions default limit at 30", () => {
    expect(APP_CONFIG.DEFAULT_PREDICTIONS_LIMIT).toBe(30);
  });

  it("sets the default client timeout at 60s", () => {
    expect(APP_CONFIG.API_DEFAULT_TIMEOUT).toBe(60000);
  });
});

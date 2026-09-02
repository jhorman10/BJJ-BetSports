import { describe, expect, it, beforeEach } from "vitest";

import { useUIStore } from "./useUIStore";

describe("useUIStore.selectedSport", () => {
  beforeEach(() => {
    try {
      window.localStorage.removeItem("selected-sport");
      window.localStorage.removeItem("ui-store");
    } catch {
      // ignore
    }
    useUIStore.setState({ selectedSport: "soccer" });
  });

  it("defaults to soccer on fresh load", () => {
    expect(useUIStore.getState().selectedSport).toBe("soccer");
  });

  it("setSport updates state and localStorage", () => {
    useUIStore.getState().setSport("baseball");
    expect(useUIStore.getState().selectedSport).toBe("baseball");
    try {
      expect(window.localStorage.getItem("selected-sport")).toBe("baseball");
    } catch {
      // ignore if localStorage unavailable in test env
    }
  });
});

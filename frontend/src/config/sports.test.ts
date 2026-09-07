import { describe, expect, it } from "vitest";

import { SPORTS, DEFAULT_SPORT } from "./constants";

describe("SPORTS", () => {
  it("defines exactly three sports with display labels", () => {
    expect(SPORTS).toHaveLength(3);
    const values = SPORTS.map((s) => s.value);
    expect(values).toEqual(["soccer", "tennis", "baseball"]);
  });

  it("labels are Spanish display strings", () => {
    expect(SPORTS.find((s) => s.value === "soccer")?.label).toBe("Fútbol");
    expect(SPORTS.find((s) => s.value === "tennis")?.label).toBe("Tenis");
    expect(SPORTS.find((s) => s.value === "baseball")?.label).toBe("Béisbol");
  });
});

describe("DEFAULT_SPORT", () => {
  it("defaults to soccer (backward compatible)", () => {
    expect(DEFAULT_SPORT).toBe("soccer");
  });
});

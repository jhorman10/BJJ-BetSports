import { describe, expect, it } from "vitest";

import { SPORTS, DEFAULT_SPORT } from "./constants";

describe("SPORTS", () => {
  it("defines exactly four sports with display labels", () => {
    expect(SPORTS).toHaveLength(4);
    const values = SPORTS.map((s) => s.value);
    expect(values).toEqual(["soccer", "tennis", "baseball", "basketball"]);
  });

  it("labels are Spanish display strings", () => {
    expect(SPORTS.find((s) => s.value === "soccer")?.label).toBe("Fútbol");
    expect(SPORTS.find((s) => s.value === "tennis")?.label).toBe("Tenis");
    expect(SPORTS.find((s) => s.value === "baseball")?.label).toBe("Béisbol");
    expect(SPORTS.find((s) => s.value === "basketball")?.label).toBe(
      "Baloncesto"
    );
  });
});

describe("DEFAULT_SPORT", () => {
  it("defaults to soccer (backward compatible)", () => {
    expect(DEFAULT_SPORT).toBe("soccer");
  });
});

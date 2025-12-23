import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import PredictionGridHeader from "./PredictionGridHeader";
import { League } from "../../../types";

const mockLeague: League = {
  id: "1",
  name: "La Liga",
  country: "Spain",
  season: "2024",
};

describe("PredictionGridHeader", () => {
  it("renders league info correctly", () => {
    render(
      <PredictionGridHeader
        league={mockLeague}
        predictionCount={5}
        onSortChange={vi.fn()}
        sortBy="confidence"
        searchQuery=""
        onSearchChange={vi.fn()}
      />
    );

    expect(screen.getByText(/Predicciones: La Liga/i)).toBeInTheDocument();
    expect(screen.getByText(/5 partidos analizados/i)).toBeInTheDocument();
  });
});

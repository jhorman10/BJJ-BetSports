import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import PredictionGridHeader from "./PredictionGridHeader";
import { League } from "../../types";

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
        showLiveOnly={false}
        onLiveToggle={vi.fn()}
        sortBy="confidence"
        onSortChange={vi.fn()}
      />
    );

    expect(screen.getByText(/Predicciones: La Liga/i)).toBeInTheDocument();
    expect(screen.getByText(/5 partidos analizados/i)).toBeInTheDocument();
  });

  it("triggers live toggle", () => {
    const toggleMock = vi.fn();
    render(
      <PredictionGridHeader
        league={mockLeague}
        predictionCount={5}
        showLiveOnly={false}
        onLiveToggle={toggleMock}
        sortBy="confidence"
        onSortChange={vi.fn()}
      />
    );

    fireEvent.click(screen.getByText(/EN VIVO/i));
    expect(toggleMock).toHaveBeenCalled();
  });
});

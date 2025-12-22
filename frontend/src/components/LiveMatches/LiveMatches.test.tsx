import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import LiveMatches from "./LiveMatches";
import api from "../../services/api"; // We will mock this

// Mock the API module
vi.mock("../../services/api", () => ({
  default: {
    getLiveMatches: vi.fn(),
  },
}));

describe("LiveMatches", () => {
  it("renders loading state initially", async () => {
    // Mock return value to never resolve immediately to test loading state
    (api.getLiveMatches as any).mockReturnValue(new Promise(() => {}));

    render(<LiveMatches />);
    // Initial render might be null until effect kicks in, but loading state uses processingMessage "Actualizando marcadores..."
    // We expect "Partidos en Vivo" title which is present in Loading state
    expect(screen.getByText("Partidos en Vivo")).toBeInTheDocument();
    expect(screen.getByText("Actualizando marcadores...")).toBeInTheDocument();
  });

  it("renders live matches when API returns data", async () => {
    const mockMatches = [
      {
        id: "1",
        home_team: "HomeFC",
        away_team: "AwayFC", // The hook expects string for team names now
        home_score: 1,
        away_score: 0,
        status: "LIVE",
        match_date: "2024-01-01T12:00:00Z",
      },
    ];

    (api.getLiveMatches as any).mockResolvedValue(mockMatches);

    render(<LiveMatches />);

    await waitFor(
      () => {
        expect(screen.getAllByText("Partidos en Vivo")[0]).toBeInTheDocument();
        expect(screen.getByText("HomeFC")).toBeInTheDocument();
        expect(screen.getByText("AwayFC")).toBeInTheDocument();
        expect(screen.getByText("1 - 0")).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });

  it("renders mock data if API fails", async () => {
    (api.getLiveMatches as any).mockRejectedValue(new Error("API Error"));

    render(<LiveMatches />);

    await waitFor(
      () => {
        // Should render Fallback Mock data (Flamengo vs Fluminense from hook)
        expect(screen.getByText("Flamengo")).toBeInTheDocument();
      },
      { timeout: 2000 }
    );
  });
});

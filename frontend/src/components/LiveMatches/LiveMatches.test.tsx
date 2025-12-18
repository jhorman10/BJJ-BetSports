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
  it("renders loading state initially", () => {
    // Mock return value to never resolve immediately to test loading state
    (api.getLiveMatches as any).mockReturnValue(new Promise(() => {}));

    render(<LiveMatches />);
    expect(
      screen.getByText("Cargando partidos en vivo...")
    ).toBeInTheDocument();
  });

  it("renders live matches when API returns data", async () => {
    const mockMatches = [
      {
        id: "1",
        home_team: { id: "h1", name: "HomeFC" },
        away_team: { id: "a1", name: "AwayFC" },
        league: { id: "l1", name: "Premier League" },
        status: "LIVE",
        home_goals: 1,
        away_goals: 0,
        match_date: "2024-01-01T12:00:00Z",
      },
    ];

    (api.getLiveMatches as any).mockResolvedValue(mockMatches);

    render(<LiveMatches />);

    await waitFor(() => {
      expect(screen.getByText("Partidos en Vivo Ahora")).toBeInTheDocument();
      expect(screen.getByText("HomeFC")).toBeInTheDocument();
      expect(screen.getByText("AwayFC")).toBeInTheDocument();
      expect(screen.getByText("1 - 0")).toBeInTheDocument();
    });
  });

  it("renders nothing if API fails", async () => {
    (api.getLiveMatches as any).mockRejectedValue(new Error("API Error"));

    const { container } = render(<LiveMatches />);

    await waitFor(() => {
      // If error, component returns null
      expect(container.firstChild).toBeNull();
    });
  });
});

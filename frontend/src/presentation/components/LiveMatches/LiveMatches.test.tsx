import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

import { useLiveMatches, LiveMatch } from "../../../hooks/useLiveMatches";

import LiveMatches from "./LiveMatches";

// Mock the hook
vi.mock("../../../hooks/useLiveMatches", () => ({
  useLiveMatches: vi.fn(),
}));

describe("LiveMatches", () => {
  it("renders loading state initially", () => {
    vi.mocked(useLiveMatches).mockReturnValue({
      matches: [],
      loading: true,
      error: null,
      refresh: vi.fn(),
    });

    render(<LiveMatches />);
    expect(screen.getByText("Partidos en Vivo")).toBeInTheDocument();
    expect(screen.getByText("Actualizando marcadores...")).toBeInTheDocument();
  });

  it("renders live matches when data is present", () => {
    const mockMatches: LiveMatch[] = [
      {
        id: "1",
        home_team: "HomeFC",
        away_team: "AwayFC",
        home_score: 1,
        away_score: 0,
        status: "LIVE",
        minute: 10,
        league_id: "L1",
        league_name: "Test League",
        home_corners: 0,
        away_corners: 0,
        home_yellow_cards: 0,
        away_yellow_cards: 0,
        home_red_cards: 0,
        away_red_cards: 0,
        prediction: undefined,
      },
    ];

    vi.mocked(useLiveMatches).mockReturnValue({
      matches: mockMatches,
      loading: false,
      error: null,
      refresh: vi.fn(),
    });

    render(<LiveMatches />);
    expect(screen.getByText("HomeFC")).toBeInTheDocument();
    expect(screen.getByText("AwayFC")).toBeInTheDocument();
    expect(screen.getByText("1 - 0")).toBeInTheDocument();
  });

  it("hides section on error or empty matches", () => {
    vi.mocked(useLiveMatches).mockReturnValue({
      matches: [],
      loading: false,
      error: "API Error",
      refresh: vi.fn(),
    });

    const { container } = render(<LiveMatches />);
    expect(container.firstChild).toBeNull();
  });
});

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import LiveMatches from "./LiveMatches";
import * as useLiveMatchesHook from "../../../hooks/useLiveMatches";

// Mock the hook
vi.mock("../../../hooks/useLiveMatches", () => ({
  useLiveMatches: vi.fn(),
}));

describe("LiveMatches", () => {
  it("renders loading state initially", () => {
    (useLiveMatchesHook.useLiveMatches as any).mockReturnValue({
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
    const mockMatches = [
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
      },
    ];

    (useLiveMatchesHook.useLiveMatches as any).mockReturnValue({
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
    (useLiveMatchesHook.useLiveMatches as any).mockReturnValue({
      matches: [],
      loading: false,
      error: "API Error",
      refresh: vi.fn(),
    });

    const { container } = render(<LiveMatches />);
    expect(container.firstChild).toBeNull();
  });
});

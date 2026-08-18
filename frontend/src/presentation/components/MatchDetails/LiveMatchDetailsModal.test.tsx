import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  LiveMatchPrediction,
  Match,
  MatchPrediction,
  Prediction,
} from "../../../domain/entities";
import { useLiveStore } from "../../../application/stores/useLiveStore";
import { useUIStore } from "../../../application/stores/useUIStore";

import LiveMatchDetailsModal from "./LiveMatchDetailsModal";

vi.mock("../../../application/stores/useUIStore", () => ({
  useUIStore: vi.fn(),
}));

vi.mock("../../../application/stores/useLiveStore", () => ({
  useLiveStore: vi.fn(),
}));

vi.mock("./components/LiveScoreBoard", () => ({
  LiveScoreBoard: () => <div data-testid="live-score-board" />,
}));

vi.mock("./components/LiveMatchStats", () => ({
  LiveMatchStats: () => <div data-testid="live-match-stats" />,
}));

vi.mock("./SuggestedPicksTab", () => ({
  default: () => <div data-testid="suggested-picks" />,
}));

const mockUseUIStore = vi.mocked(useUIStore);
const mockUseLiveStore = vi.mocked(useLiveStore);

const makePrediction = (overrides: Partial<Prediction> = {}): Prediction => ({
  match_id: "401903297",
  home_win_probability: 0.33,
  draw_probability: 0.34,
  away_win_probability: 0.33,
  over_25_probability: 0.4,
  under_25_probability: 0.6,
  predicted_home_goals: 1.0,
  predicted_away_goals: 1.0,
  confidence: 0,
  data_sources: ["live_match_fallback"],
  recommended_bet: "Sin recomendacion",
  over_under_recommendation: "Sin recomendacion",
  created_at: "2026-08-11T10:00:00Z",
  ...overrides,
});

const makeMatch = (): Match => ({
  id: "401903297",
  home_team: { id: "h1", name: "Real Madrid" },
  away_team: { id: "a1", name: "Barcelona" },
  league: { id: "esp.1", name: "La Liga", country: "Spain" },
  match_date: "2026-08-11T20:00:00Z",
  home_goals: 0,
  away_goals: 0,
  status: "LIVE",
  minute: "11'",
  home_corners: 1,
  away_corners: 0,
});

const makeSelectedMatch = (
  prediction: Prediction,
  match: Match = makeMatch()
): MatchPrediction => ({ match, prediction });

const renderModal = (
  selected: MatchPrediction,
  liveMatches: LiveMatchPrediction[] = []
): ReturnType<typeof render> => {
  mockUseUIStore.mockReturnValue({
    liveModalOpen: true,
    selectedLiveMatch: selected,
    closeLiveMatchModal: vi.fn(),
  } as unknown as ReturnType<typeof useUIStore>);
  mockUseLiveStore.mockReturnValue({
    matches: liveMatches,
  } as unknown as ReturnType<typeof useLiveStore>);
  return render(<LiveMatchDetailsModal />);
};

describe("LiveMatchDetailsModal prediction honesty gate", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows the no-prediction state for fallback-only predictions, never the 33% bars", () => {
    const fallbackPrediction = makePrediction(); // data_sources ["live_match_fallback"], hwp 0.33
    renderModal(makeSelectedMatch(fallbackPrediction));

    expect(
      screen.getByText("No hay predicción pre-partido disponible para este evento.")
    ).toBeInTheDocument();
    // The fabricated fallback must never render as a real prediction
    expect(
      screen.queryByText(/Predicción Pre-Partido/)
    ).not.toBeInTheDocument();
    expect(screen.queryByText("33%")).not.toBeInTheDocument();
    // Suggested picks section is gated off too
    expect(screen.queryByTestId("suggested-picks")).not.toBeInTheDocument();
  });

  it("renders the full pre-match prediction UI for a genuine prediction", () => {
    const realPrediction = makePrediction({
      home_win_probability: 0.6,
      draw_probability: 0.2,
      away_win_probability: 0.2,
      confidence: 0.6,
      data_sources: ["Rigorous ML"],
    });
    renderModal(makeSelectedMatch(realPrediction));

    expect(
      screen.queryByText("No hay predicción pre-partido disponible para este evento.")
    ).not.toBeInTheDocument();
    expect(screen.getByText(/Predicción Pre-Partido/)).toBeInTheDocument();
    expect(screen.getByText("Probabilidad Local")).toBeInTheDocument();
    expect(screen.getByTestId("suggested-picks")).toBeInTheDocument();
  });

  it("keeps the no-prediction state even when the live store provides a fallback update", () => {
    const fallbackPrediction = makePrediction();
    const selected = makeSelectedMatch(fallbackPrediction);
    // Live store has the same fallback stub (confidence 0) — still not real
    const liveStub: LiveMatchPrediction = {
      match: selected.match,
      prediction: fallbackPrediction,
      isProcessing: true,
    };
    renderModal(selected, [liveStub]);

    expect(
      screen.getByText("No hay predicción pre-partido disponible para este evento.")
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Predicción Pre-Partido/)
    ).not.toBeInTheDocument();
  });
});

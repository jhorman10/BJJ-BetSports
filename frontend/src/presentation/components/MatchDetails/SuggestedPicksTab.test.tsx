import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { act, ReactElement } from "react";

import {
  Match,
  MatchPrediction,
  Prediction,
  SuggestedPick,
} from "../../../types";
import { useCacheStore } from "../../../application/stores/useCacheStore";

import SuggestedPicksTab from "./SuggestedPicksTab";

vi.mock("../../../application/stores/useCacheStore", () => ({
  useCacheStore: vi.fn(),
}));

const mockUseCacheStore = vi.mocked(useCacheStore);

const MATCH_ID = "401903297";

const makeMatch = (): Match => ({
  id: MATCH_ID,
  home_team: { id: "h1", name: "Real Madrid" },
  away_team: { id: "a1", name: "Barcelona" },
  league: { id: "esp.1", name: "La Liga", country: "Spain" },
  match_date: "2026-08-13T20:00:00Z",
  status: "SCHEDULED",
});

const makePick = (overrides: Partial<SuggestedPick>): SuggestedPick => ({
  market_type: "goals_over_2_5",
  market_label: "Over 2.5 goles",
  probability: 0.75,
  confidence_level: "high",
  reasoning: "Alta probabilidad de goles en el partido",
  risk_level: 0.4,
  is_recommended: true,
  priority_score: 1,
  ...overrides,
});

// Category fixtures: exact market_type strings handled by getMarketCategory
const goalsPick = makePick({
  market_type: "goals_over_2_5",
  market_label: "Over 2.5 goles",
  pick_code: "O2.5",
});
const cornersPick = makePick({
  market_type: "corners_over_9_5",
  market_label: "Más de 9.5 córners",
  probability: 0.62,
  pick_code: "O9.5",
});
// Top ML pick: same market family as goalsPick, but flagged is_ml_confirmed
// (+ reasoning tag) so it must only ever appear in the "🔥 Top ML" tab.
const topMlGoalsPick = makePick({
  market_type: "goals_over_1_5",
  market_label: "Over 1.5 goles (ML)",
  probability: 0.88,
  is_ml_confirmed: true,
  ml_confidence: 0.91,
  reasoning: "[⭐ ML ALTA CONFIANZA] Goles casi asegurados por el modelo",
  pick_code: "O1.5",
});
// IA-confirmed variant (isTopMLPick also matches is_ia_confirmed).
const topMlCornersPick = makePick({
  market_type: "corners_over_8_5",
  market_label: "Más de 8.5 córners (ML)",
  probability: 0.86,
  is_ia_confirmed: true,
  reasoning: "[🎯 IA CONFIRMED] Córners dominados por el modelo",
  pick_code: "O8.5",
});
// Same market (corners_over_9_5) with TWO line variants: an ML-confirmed line
// and a NON-ML line. The whole market must belong to Top ML only - the non-ML
// line must never leak into the regular Córners tab.
const cornersMlPick = makePick({
  market_type: "corners_over_9_5",
  market_label: "Más de 9.5 córners",
  probability: 0.62,
  is_ml_confirmed: true,
  ml_confidence: 0.88,
  reasoning: "[⭐ ML ALTA CONFIANZA] Córners dominados por el modelo",
  pick_code: "O9.5",
});
const cornersNonMlVariantPick = makePick({
  market_type: "corners_over_9_5",
  market_label: "Más de 10.5 córners",
  probability: 0.55,
  reasoning: "Línea alternativa de córners",
  pick_code: "O10.5",
});
// Lower-probability second line of the SAME goals market (no ML flag): both
// variants share market_type goals_over_2_5, so only the best one may render.
const goalsLowerVariantPick = makePick({
  market_type: "goals_over_2_5",
  market_label: "Over 2.5 goles (línea alternativa)",
  probability: 0.71,
  pick_code: "O2.5B",
});

const makePrediction = (picks: SuggestedPick[]): Prediction => ({
  match_id: MATCH_ID,
  home_win_probability: 0.55,
  draw_probability: 0.25,
  away_win_probability: 0.2,
  over_25_probability: 0.6,
  under_25_probability: 0.4,
  predicted_home_goals: 1.8,
  predicted_away_goals: 1.2,
  confidence: 0.6,
  data_sources: ["Rigorous ML"],
  recommended_bet: "Over 2.5",
  over_under_recommendation: "Over 2.5",
  created_at: "2026-08-13T10:00:00Z",
  suggested_picks: picks,
});

const buildSubject = (
  picks: SuggestedPick[],
  onPicksCount?: (count: number) => void
): ReactElement => {
  const matchPrediction: MatchPrediction = {
    match: makeMatch(),
    prediction: makePrediction(picks),
  };
  return (
    <SuggestedPicksTab
      matchPrediction={matchPrediction}
      onPicksCount={onPicksCount}
    />
  );
};

describe("SuggestedPicksTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseCacheStore.mockReturnValue({
      getPicks: vi.fn(() => null),
      prefetchMatch: vi.fn(() => Promise.resolve()),
      isFetching: vi.fn(() => false),
    } as unknown as ReturnType<typeof useCacheStore>);
  });

  it("auto-selects the first available tab (Goles) and renders only its picks", () => {
    render(buildSubject([goalsPick, cornersPick]));

    // Priority order puts GOALS before CORNERS: Goles must be the active tab.
    expect(screen.getByRole("tab", { name: "Goles" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByRole("tab", { name: "Córners" })).toHaveAttribute(
      "aria-selected",
      "false"
    );

    // Only GOALS-category content is rendered; CORNERS picks must NOT leak in.
    expect(screen.getByText("Over 2.5 goles")).toBeInTheDocument();
    expect(screen.queryByText("Más de 9.5 córners")).not.toBeInTheDocument();
  });

  it("switches rendered content when clicking the Córners and Goles tabs", async () => {
    const user = userEvent.setup();
    render(buildSubject([goalsPick, cornersPick]));

    // Initially only GOALS picks are visible.
    expect(screen.getByText("Over 2.5 goles")).toBeInTheDocument();
    expect(screen.queryByText("Más de 9.5 córners")).not.toBeInTheDocument();

    // Click Córners -> content must swap to CORNERS-category picks only.
    await user.click(screen.getByRole("tab", { name: "Córners" }));
    expect(screen.getByText("Más de 9.5 córners")).toBeInTheDocument();
    expect(screen.queryByText("Over 2.5 goles")).not.toBeInTheDocument();

    // Click Goles again -> content swaps back to GOALS-category picks only.
    await user.click(screen.getByRole("tab", { name: "Goles" }));
    expect(screen.getByText("Over 2.5 goles")).toBeInTheDocument();
    expect(screen.queryByText("Más de 9.5 córners")).not.toBeInTheDocument();
  });

  it("keeps Top ML picks isolated from every standard tab's content", async () => {
    const user = userEvent.setup();
    render(buildSubject([topMlGoalsPick, goalsPick, cornersPick]));

    // Top ML is first in priority order, so it is the auto-selected tab.
    expect(screen.getByRole("tab", { name: /Top ML/ })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByText("Over 1.5 goles (ML)")).toBeInTheDocument();
    expect(screen.queryByText("Over 2.5 goles")).not.toBeInTheDocument();
    expect(screen.queryByText("Más de 9.5 córners")).not.toBeInTheDocument();

    // The ML-confirmed pick must NOT appear in the Goles tab, even though its
    // market_type (goals_over_1_5) belongs to the GOALS category.
    await user.click(screen.getByRole("tab", { name: "Goles" }));
    expect(screen.getByText("Over 2.5 goles")).toBeInTheDocument();
    expect(screen.queryByText("Over 1.5 goles (ML)")).not.toBeInTheDocument();

    // Nor in the Córners tab.
    await user.click(screen.getByRole("tab", { name: "Córners" }));
    expect(screen.getByText("Más de 9.5 córners")).toBeInTheDocument();
    expect(screen.queryByText("Over 1.5 goles (ML)")).not.toBeInTheDocument();

    // Switching back to Top ML restores it.
    await user.click(screen.getByRole("tab", { name: /Top ML/ }));
    expect(screen.getByText("Over 1.5 goles (ML)")).toBeInTheDocument();
    expect(screen.queryByText("Over 2.5 goles")).not.toBeInTheDocument();
  });

  it("falls back to the first available tab when the persisted category disappears", async () => {
    const user = userEvent.setup();
    const { rerender } = render(buildSubject([goalsPick, cornersPick]));

    // User selects the Córners tab (a currently-inactive tab, so the explicit
    // selection sticks; clicking the already-active tab is a MUI no-op).
    await user.click(screen.getByRole("tab", { name: "Córners" }));

    // Same match id, but the corners pick is now promoted to Top ML, so the
    // CORNERS category disappears while the user's tab selection persists.
    // async act: React 19 flushes MUI Tabs' internal effects (scroll/selected
    // tab state) outside a sync act scope, which would trip act() warnings.
    await act(async () => {
      rerender(buildSubject([goalsPick, topMlCornersPick]));
    });

    // S1 guard: the stale selection must not feed Tabs an invalid value. The
    // component auto-selects the first available tab (Top ML, priority #1)
    // and renders ITS picks; the vanished category is gone from the UI.
    expect(screen.getByRole("tab", { name: /Top ML/ })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(
      screen.queryByRole("tab", { name: "Córners" })
    ).not.toBeInTheDocument();
    expect(screen.getByText("Más de 8.5 córners (ML)")).toBeInTheDocument();
    expect(screen.queryByText("Más de 9.5 córners")).not.toBeInTheDocument();
  });

  it("reports the number of rendered markets (one per market_type) through onPicksCount", () => {
    const onPicksCount = vi.fn();
    render(buildSubject([goalsPick, cornersPick, topMlGoalsPick], onPicksCount));

    expect(onPicksCount).toHaveBeenCalledTimes(1);
    expect(onPicksCount).toHaveBeenCalledWith(3);
  });

  it("reports the number of rendered markets, deduping line variants that share a market_type", () => {
    const onPicksCount = vi.fn();
    render(
      buildSubject([goalsPick, goalsLowerVariantPick, cornersPick], onPicksCount)
    );

    // goalsPick and goalsLowerVariantPick share market_type goals_over_2_5
    // (different labels, no ML flags): the UI renders one pick per market via
    // uniqueByMarket, so only 2 markets are reported, not 3 raw picks.
    expect(onPicksCount).toHaveBeenCalledTimes(1);
    expect(onPicksCount).toHaveBeenCalledWith(2);
  });

  it("reserves an entire market for Top ML, hiding its non-ML line variants from regular tabs", async () => {
    const user = userEvent.setup();
    render(buildSubject([cornersMlPick, cornersNonMlVariantPick, goalsPick]));

    // The market corners_over_9_5 has a Top ML pick, so Top ML is auto-selected
    // and renders the ML line only.
    expect(screen.getByRole("tab", { name: /Top ML/ })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByText("Más de 9.5 córners")).toBeInTheDocument();
    expect(screen.queryByText("Más de 10.5 córners")).not.toBeInTheDocument();

    // The whole market is owned by Top ML: no Córners tab is rendered at all,
    // so the non-ML line variant can never repeat in a regular tab.
    expect(screen.queryByRole("tab", { name: "Córners" })).not.toBeInTheDocument();

    // Other tabs still render their own picks; the duplicated market never leaks.
    await user.click(screen.getByRole("tab", { name: "Goles" }));
    expect(screen.getByText("Over 2.5 goles")).toBeInTheDocument();
    expect(screen.queryByText("Más de 9.5 córners")).not.toBeInTheDocument();
    expect(screen.queryByText("Más de 10.5 córners")).not.toBeInTheDocument();
  });

  it("dedupes picks by market, rendering each market only once per tab", () => {
    render(buildSubject([goalsPick, goalsLowerVariantPick]));

    // Goles is auto-selected: both variants share market_type goals_over_2_5,
    // so only the best (higher probability) line is rendered.
    expect(screen.getByRole("tab", { name: "Goles" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getAllByText("Over 2.5 goles")).toHaveLength(1);
    expect(
      screen.queryByText("Over 2.5 goles (línea alternativa)")
    ).not.toBeInTheDocument();
  });

  it("renders fallback picks when no picks are provided and a prediction exists", () => {
    render(buildSubject([]));

    // With an empty pick list and a prediction present, generateFallbackPicks
    // fills the tab with derived picks (goals_over is the auto-selected
    // default here) — this is NOT the "no picks" empty state, which needs the
    // pre-tabs guard to trigger.
    expect(screen.getByRole("tab", { name: "Goles" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByText("Más de 2.5 Goles")).toBeInTheDocument();
    expect(
      screen.queryByText("No hay picks en esta categoría")
    ).not.toBeInTheDocument();
  });
});

/**
 * MatchCard modal-overlap regression tests
 *
 * Bug report: clicking the "Marcador Tentativo" badge inside a card opened BOTH
 * modals ("Detalles del Partido" on top, "Marcador Tentativo" behind). Closing
 * the top modal left the bottom one open, and any interaction inside the
 * leftover modal (even closing it) RE-OPENED "Detalles del Partido" — an
 * infinite open/close loop.
 *
 * Acceptance criteria covered:
 *  - A: badge click opens ONLY the score matrix modal (details modal never opens)
 *  - B: closing the score matrix modal closes everything cleanly, no reopen loop
 *  - C: clicking the card outside the badge still opens the details modal
 *  - D: interaction inside the score matrix modal does NOT reopen the details modal
 *
 * The harness mirrors PredictionGrid state semantics (grid-level
 * selectedMatch + detailsOpen) and renders 3 cards to prove index-independence.
 *
 * NOTE on queries: dialogs are queried with `hidden: true` because MUI's
 * ModalManager marks covered modals as aria-hidden when multiple modals are
 * stacked — the default role query would invisibly mask the buggy state.
 */
import React, { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { Match, MatchPrediction, Prediction } from "../../../types";
import MatchDetailsModal from "../MatchDetails/MatchDetailsModal";

import MatchCard from "./MatchCard";

// Module mocks — keep the test focused on the modal interplay, not stores.
// NOTE: no vi.clearAllMocks() in beforeEach — it wipes the factory
// implementation of this mock mid-test (Vitest 4), breaking prefetchMatch.
vi.mock("../../../application/stores/useCacheStore", () => {
  const mockState = {
    prefetchMatch: vi.fn(async () => undefined),
  };
  return {
    // Zustand-style hook: MatchCard consumes the selector form
    // `useCacheStore((state) => state.prefetchMatch)`, so the mock must APPLY
    // the selector and return the selected slice, not the whole state object.
    useCacheStore: vi.fn(
      (selector?: (state: typeof mockState) => unknown) =>
        selector ? selector(mockState) : mockState
    ),
  };
});

vi.mock("../MatchDetails/SuggestedPicksTab", () => ({
  default: () => <div data-testid="suggested-picks-stub" />,
}));

/* ------------------------------------------------------------------------- */
/* Fixtures                                                                  */
/* ------------------------------------------------------------------------- */

const makeMatch = (id: string, home: string, away: string): Match => ({
  id,
  home_team: { id: `home-${id}`, name: home },
  away_team: { id: `away-${id}`, name: away },
  league: { id: "league-1", name: "Test League", country: "Spain" },
  match_date: "2026-08-13T18:00:00Z",
  status: "NS",
  home_spi: 75.5,
  away_spi: 70.2,
});

const makePrediction = (matchId: string): Prediction => ({
  match_id: matchId,
  home_win_probability: 0.55,
  draw_probability: 0.25,
  away_win_probability: 0.2,
  over_25_probability: 0.6,
  under_25_probability: 0.4,
  predicted_home_goals: 1.9,
  predicted_away_goals: 1.1,
  confidence: 0.7,
  data_sources: ["Rigorous ML"],
  recommended_bet: "1 (Local)",
  over_under_recommendation: "Over 2.5",
  created_at: "2026-08-13T10:00:00Z",
  // Marcador Tentativo data — renders the badge in the card
  score_probabilities: [
    { home_goals: 2, away_goals: 0, probability: 0.18 },
    { home_goals: 1, away_goals: 0, probability: 0.14 },
    { home_goals: 1, away_goals: 1, probability: 0.12 },
  ],
  score_confidence_tier: "Media",
  // Renders the bell-curve chart inside the score matrix modal
  score_matrix: [
    [
      {
        home_goals: 0,
        away_goals: 0,
        probability: 0.06,
        home_xg_contribution: 1,
        away_xg_contribution: 1,
      },
      {
        home_goals: 1,
        away_goals: 0,
        probability: 0.14,
        home_xg_contribution: 2,
        away_xg_contribution: 0.5,
      },
    ],
    [
      {
        home_goals: 0,
        away_goals: 1,
        probability: 0.05,
        home_xg_contribution: 0.5,
        away_xg_contribution: 2,
      },
      {
        home_goals: 2,
        away_goals: 0,
        probability: 0.18,
        home_xg_contribution: 3,
        away_xg_contribution: 0.3,
      },
    ],
  ],
});

const makeMatchPrediction = (
  matchId: string,
  home: string,
  away: string
): MatchPrediction => ({
  match: makeMatch(matchId, home, away),
  prediction: makePrediction(matchId),
});

const THREE_PREDICTIONS: MatchPrediction[] = [
  makeMatchPrediction("m1", "Real Madrid", "Barcelona"),
  makeMatchPrediction("m2", "Atletico Madrid", "Sevilla"),
  makeMatchPrediction("m3", "Betis", "Valencia"),
];

/* ------------------------------------------------------------------------- */
/* Harness — replicates PredictionGrid modal state semantics                 */
/* (single grid-level selectedMatch + detailsOpen, one shared details modal) */
/* ------------------------------------------------------------------------- */

interface HarnessProps {
  predictions: MatchPrediction[];
}

const Harness: React.FC<HarnessProps> = ({ predictions }) => {
  const [selectedMatch, setSelectedMatch] = useState<MatchPrediction | null>(
    null
  );
  const [detailsOpen, setDetailsOpen] = useState(false);

  return (
    <>
      {predictions.map((matchPrediction, index) => (
        <MatchCard
          key={matchPrediction.match.id}
          matchPrediction={matchPrediction}
          highlight={index === 0}
          onClick={() => {
            setSelectedMatch(matchPrediction);
            setDetailsOpen(true);
          }}
        />
      ))}
      <MatchDetailsModal
        open={detailsOpen}
        onClose={() => {
          setDetailsOpen(false);
          setSelectedMatch(null);
        }}
        matchPrediction={selectedMatch}
      />
    </>
  );
};

/* ------------------------------------------------------------------------- */
/* Query helpers — hidden:true so stacked/covered MUI modals are observable  */
/* ------------------------------------------------------------------------- */

const scoreMatrixDialog = (): HTMLElement | null =>
  screen.queryByRole("dialog", {
    name: /marcador tentativo/i,
    hidden: true,
  });

const detailsDialog = (): HTMLElement | null =>
  screen.queryByRole("dialog", { name: /detalles del partido/i, hidden: true });

const allDialogs = (): HTMLElement[] =>
  screen.queryAllByRole("dialog", { hidden: true });

const clickBadge = async (
  user: ReturnType<typeof userEvent.setup>,
  cardIndex: number
): Promise<void> => {
  const badges = screen.getAllByText("🎲 Marcador Tentativo");
  await user.click(badges[cardIndex]);
};

/* ------------------------------------------------------------------------- */
/* Tests                                                                     */
/* ------------------------------------------------------------------------- */

describe("MatchCard Marcador Tentativo modal interplay", () => {
  it("A: badge click opens ONLY the score matrix modal, never the details modal", async () => {
    const user = userEvent.setup();
    render(<Harness predictions={THREE_PREDICTIONS} />);

    // Second card on purpose — proves the fix is index-independent
    await clickBadge(user, 1);

    expect(scoreMatrixDialog()).toBeInTheDocument();
    expect(detailsDialog()).not.toBeInTheDocument();
    expect(allDialogs()).toHaveLength(1);
  });

  it("B: closing the score matrix modal closes everything and never reopens the details modal", async () => {
    const user = userEvent.setup();
    render(<Harness predictions={THREE_PREDICTIONS} />);

    await clickBadge(user, 0);
    const dialog = await screen.findByRole("dialog", {
      name: /marcador tentativo/i,
      hidden: true,
    });

    // Closing click used to bubble up to the card and reopen the details modal
    await user.click(
      within(dialog).getAllByRole("button", { name: "Cerrar", hidden: true })[0]
    );

    await waitFor(() => expect(scoreMatrixDialog()).not.toBeInTheDocument());
    expect(detailsDialog()).not.toBeInTheDocument();
    expect(allDialogs()).toHaveLength(0);

    // A fresh badge click on another card still behaves (no stale state)
    await clickBadge(user, 2);
    expect(
      await screen.findByRole("dialog", {
        name: /marcador tentativo/i,
        hidden: true,
      })
    ).toBeInTheDocument();
    expect(detailsDialog()).not.toBeInTheDocument();
    expect(allDialogs()).toHaveLength(1);
  });

  it("C: clicking the card outside the badge still opens the details modal normally", async () => {
    const user = userEvent.setup();
    render(<Harness predictions={THREE_PREDICTIONS} />);

    // "Probabilidades" section heading — inside CardContent, outside the badge
    await user.click(screen.getAllByText("Probabilidades")[1]);

    expect(detailsDialog()).toBeInTheDocument();
    expect(scoreMatrixDialog()).not.toBeInTheDocument();

    // Closing the details modal leaves everything clean
    const dialog = await screen.findByRole("dialog", {
      name: /detalles del partido/i,
      hidden: true,
    });
    await user.click(
      within(dialog).getByRole("button", { name: "Cerrar", hidden: true })
    );
    await waitFor(() => expect(detailsDialog()).not.toBeInTheDocument());
    expect(scoreMatrixDialog()).not.toBeInTheDocument();
    expect(allDialogs()).toHaveLength(0);
  });

  it("D: interaction inside the score matrix modal does NOT reopen the details modal", async () => {
    const user = userEvent.setup();
    render(<Harness predictions={THREE_PREDICTIONS} />);

    await clickBadge(user, 2);
    const dialog = await screen.findByRole("dialog", {
      name: /marcador tentativo/i,
      hidden: true,
    });

    // Clicking the chart body bubbles to the card in the buggy version,
    // reopening the details modal behind the score matrix.
    await user.click(
      within(dialog).getByText("Probabilidad estimada por marcador exacto")
    );

    expect(detailsDialog()).not.toBeInTheDocument();
    expect(scoreMatrixDialog()).toBeInTheDocument();
    expect(allDialogs()).toHaveLength(1);
  });
});
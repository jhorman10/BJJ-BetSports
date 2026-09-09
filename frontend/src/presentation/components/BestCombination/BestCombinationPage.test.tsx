import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import api from "../../../services/api";
import { BestCombinationResponse } from "../../../types";

import BestCombinationPage from "./BestCombinationPage";

vi.mock("../../../services/api", () => ({
  default: { getBestCombination: vi.fn() },
}));

const SAMPLE: BestCombinationResponse = {
  legs: [
    {
      sport: "soccer",
      match_id: "m1",
      match_label: "Real Madrid vs Barcelona",
      pick_label: "ML_H",
      league: "E0",
      probability: 0.65,
      odds: 1.9,
      odds_source: "market",
      confidence_level: "high",
      is_recommended: true,
      priority_score: 90,
      confidence_warning: false,
      odds_warning: false,
    },
    {
      sport: "tennis",
      match_id: "t1",
      match_label: "Alcaraz vs Sinner",
      pick_label: "ML_H",
      league: "WTA",
      probability: 0.7,
      odds: 2.1,
      odds_source: "market",
      confidence_level: "high",
      is_recommended: true,
      priority_score: 85,
      confidence_warning: false,
      odds_warning: false,
    },
    {
      sport: "baseball",
      match_id: "b1",
      match_label: "Dodgers vs Padres",
      pick_label: "ML_H",
      league: "MLB",
      probability: 0.62,
      odds: 1.85,
      odds_source: "fair",
      confidence_level: "high",
      is_recommended: true,
      priority_score: 80,
      confidence_warning: true,
      odds_warning: true,
    },
    {
      sport: "basketball",
      match_id: "bb1",
      match_label: "Celtics vs Lakers",
      pick_label: "ML_H",
      league: "NBA",
      probability: 0.72,
      odds: 2.25,
      odds_source: "market",
      confidence_level: "high",
      is_recommended: true,
      priority_score: 95,
      confidence_warning: false,
      odds_warning: false,
    },
  ],
  aggregate: {
    total_probability: 0.2031,
    total_odds: 16.6,
    expected_value: 0.35,
    mixed_odds: true,
  },
  stake: {
    suggested_stake_pct: 0.025,
    risk_level: 2,
    kelly_fraction: 0.25,
  },
  generated_at: "2026-09-08T10:00:00Z",
  independence_disclaimer:
    "Combinada armada sobre eventos independientes de cuatro deportes distintos.",
  warnings: [],
};

describe("BestCombinationPage", () => {
  beforeEach(() => {
    vi.mocked(api.getBestCombination).mockReset();
  });

  it("shows a loading state while asking the model", async () => {
    vi.mocked(api.getBestCombination).mockImplementation(
      () => new Promise(() => {})
    );
    const user = userEvent.setup();
    render(<BestCombinationPage />);

    await user.click(
      screen.getByRole("button", { name: /Pregúntale al modelo/i })
    );

    expect(
      screen.getByText(/Consultando los modelos de los cuatro deportes/i)
    ).toBeInTheDocument();
  });

  it("shows the backend detail message when the request fails", async () => {
    vi.mocked(api.getBestCombination).mockRejectedValue({
      response: {
        data: {
          detail: "No hay suficientes picks de alta confianza en 2 deportes.",
        },
      },
    });
    const user = userEvent.setup();
    render(<BestCombinationPage />);

    await user.click(
      screen.getByRole("button", { name: /Pregúntale al modelo/i })
    );

    expect(
      await screen.findByText(
        "No hay suficientes picks de alta confianza en 2 deportes."
      )
    ).toBeInTheDocument();
  });

  it("shows the nested detail of an object-detail 409 error", async () => {
    // Backend 409 contract: { error, detail, missing_sports }
    vi.mocked(api.getBestCombination).mockRejectedValue({
      response: {
        data: {
          detail: {
            error: "insufficient_pool",
            detail: "No hay suficientes picks para armar una combinada de cuatro piernas.",
            missing_sports: ["basketball"],
          },
        },
      },
    });
    const user = userEvent.setup();
    render(<BestCombinationPage />);

    await user.click(
      screen.getByRole("button", { name: /Pregúntale al modelo/i })
    );

    expect(
      await screen.findByText(
        "No hay suficientes picks para armar una combinada de cuatro piernas."
      )
    ).toBeInTheDocument();
    expect(screen.queryByText(/Inténtalo de nuevo/i)).not.toBeInTheDocument();
  });

  it("joins Pydantic 422 array details into a message", async () => {
    vi.mocked(api.getBestCombination).mockRejectedValue({
      response: {
        data: {
          detail: [
            {
              loc: ["body", "min_probability"],
              msg: "Input should be less than 1",
              type: "less_than",
            },
          ],
        },
      },
    });
    const user = userEvent.setup();
    render(<BestCombinationPage />);

    await user.click(
      screen.getByRole("button", { name: /Pregúntale al modelo/i })
    );

    expect(
      await screen.findByText("Input should be less than 1")
    ).toBeInTheDocument();
  });

  it("shows the generic fallback when the error carries no detail", async () => {
    vi.mocked(api.getBestCombination).mockRejectedValue(new Error("network"));
    const user = userEvent.setup();
    render(<BestCombinationPage />);

    await user.click(
      screen.getByRole("button", { name: /Pregúntale al modelo/i })
    );

    expect(
      await screen.findByText(
        "No se pudo calcular la mejor combinación. Inténtalo de nuevo."
      )
    ).toBeInTheDocument();
  });

  it("shows an empty state when the response has no legs", async () => {
    vi.mocked(api.getBestCombination).mockResolvedValue({
      ...SAMPLE,
      legs: [],
    });
    const user = userEvent.setup();
    render(<BestCombinationPage />);

    await user.click(
      screen.getByRole("button", { name: /Pregúntale al modelo/i })
    );

    expect(
      await screen.findByText(/No hay jugadas disponibles en este momento/i)
    ).toBeInTheDocument();
  });

  it("renders the four legs, aggregates and stake suggestion", async () => {
    vi.mocked(api.getBestCombination).mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    render(<BestCombinationPage />);

    await user.click(
      screen.getByRole("button", { name: /Pregúntale al modelo/i })
    );

    expect(await screen.findByText("Real Madrid vs Barcelona")).toBeInTheDocument();
    expect(screen.getByText("Alcaraz vs Sinner")).toBeInTheDocument();
    expect(screen.getByText("Dodgers vs Padres")).toBeInTheDocument();
    expect(screen.getByText("Celtics vs Lakers")).toBeInTheDocument();
    expect(screen.getByText("20.3%")).toBeInTheDocument(); // total probability
    expect(screen.getByText("16.60")).toBeInTheDocument(); // total odds
    expect(screen.getByText("35.0%")).toBeInTheDocument(); // expected value
    expect(screen.getByText("2.5%")).toBeInTheDocument(); // suggested stake
    expect(screen.getByText(/Riesgo moderado/)).toBeInTheDocument();
  });

  it("renders confidence and odds warnings for affected legs", async () => {
    vi.mocked(api.getBestCombination).mockResolvedValue(SAMPLE);
    const user = userEvent.setup();
    render(<BestCombinationPage />);

    await user.click(
      screen.getByRole("button", { name: /Pregúntale al modelo/i })
    );

    expect(
      await screen.findByText("Confianza reducida")
    ).toBeInTheDocument();
    expect(screen.getByText("Sin cuota de mercado")).toBeInTheDocument();
  });
});
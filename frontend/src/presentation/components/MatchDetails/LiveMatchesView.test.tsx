import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LiveMatchesView from "./LiveMatchesView";

const offlineStoreMock = vi.hoisted(() => ({
  isOnline: true,
  isBackendAvailable: true,
}));

vi.mock("../../../application/stores/useOfflineStore", () => ({
  useOfflineStore: () => offlineStoreMock,
}));

describe("LiveMatchesView", () => {
  beforeEach(() => {
    offlineStoreMock.isOnline = true;
    offlineStoreMock.isBackendAvailable = true;
  });

  it("shows an offline-specific message when there is no internet", () => {
    offlineStoreMock.isOnline = false;

    render(
      <LiveMatchesView
        matches={[]}
        loading={false}
        error={null}
        onRefresh={vi.fn()}
      />
    );

    expect(
      screen.getByText("Sin internet no se pueden cargar partidos en vivo.")
    ).toBeInTheDocument();
  });

  it("shows the selected-leagues empty state when online and filtered", () => {
    render(
      <LiveMatchesView
        matches={[]}
        loading={false}
        error={null}
        onRefresh={vi.fn()}
        selectedLeagueIds={["eng.1"]}
        selectedLeagueNames={["Premier League"]}
      />
    );

    expect(
      screen.getByText("No hay partidos en vivo en las ligas seleccionadas.")
    ).toBeInTheDocument();
  });
});
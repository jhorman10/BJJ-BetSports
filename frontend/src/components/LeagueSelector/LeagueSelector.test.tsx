import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, renderHook } from "@testing-library/react";
import LeagueSelector from "./LeagueSelector";
import { useLeagues } from "../../hooks/useLeagues";
import { Country, League } from "../../types";

// Mock API
vi.mock("../../services/api", () => ({
  default: {
    getLeagues: vi.fn(),
  },
}));

// Mock data
const mockLeagues: League[] = [
  { id: "1", name: "Premier League", country: "England" },
  { id: "2", name: "La Liga", country: "Spain" },
];

const mockCountries: Country[] = [
  {
    name: "England",
    code: "en",
    leagues: [mockLeagues[0]],
  },
  {
    name: "Spain",
    code: "es",
    leagues: [mockLeagues[1]],
  },
];

describe("LeagueSelector Component", () => {
  const defaultProps = {
    countries: mockCountries,
    selectedCountry: null,
    selectedLeague: null,
    onCountryChange: vi.fn(),
    onLeagueChange: vi.fn(),
    loading: false,
  };

  it("renders loading state correctly", () => {
    render(<LeagueSelector {...defaultProps} loading={true} />);
    expect(screen.getByText("Cargando ligas...")).toBeInTheDocument();
  });

  it("renders empty state correctly", () => {
    // Note: Since MUI Select is complex, we check for static texts
    render(<LeagueSelector {...defaultProps} />);
    expect(screen.getByText("Selecciona una Liga")).toBeInTheDocument();
  });

  it("shows selected country name after selection", () => {
    render(
      <LeagueSelector {...defaultProps} selectedCountry={mockCountries[0]} />
    );

    // Check for country name in select value display area if visible
    // This is tricky with MUI selects in simple unit tests, usually integration tests are better
    expect(screen.getByText("Inglaterra")).toBeInTheDocument();
  });
});

describe("useLeagues Hook", () => {
  // Reset mocks
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("initializes with default state", () => {
    const { result } = renderHook(() => useLeagues());
    expect(result.current.countries).toEqual([]);
    expect(result.current.loading).toBe(true);
  });
});

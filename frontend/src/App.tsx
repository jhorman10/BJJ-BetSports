/**
 * Main Application Component
 *
 * Football Betting Prediction Bot - Frontend
 */

import React, { useState, useEffect } from "react";
import {
  Container,
  Box,
  Typography,
  AppBar,
  Toolbar,
  Alert,
  Button,
  IconButton,
  Tooltip,
} from "@mui/material";
import { SportsSoccer, GetApp, SmartToy, Dashboard } from "@mui/icons-material";
import LeagueSelector from "./components/LeagueSelector";
import PredictionGrid from "./components/PredictionGrid";
import LiveMatchesList from "./components/MatchDetails/LiveMatchesList";
import ParleySlip, { ParleyPickItem } from "./components/Parley/ParleySlip";
import BotDashboard from "./components/BotDashboard/BotDashboard";

import { Country } from "./types";
import {
  useLeagues,
  usePredictions,
  useLeagueSelection,
} from "./hooks/usePredictions";
import { useTeamSearch } from "./hooks/useTeamSearch";

// Extend window type for PWA install event
declare global {
  interface WindowEventMap {
    beforeinstallprompt: BeforeInstallPromptEvent;
  }
  interface BeforeInstallPromptEvent extends Event {
    prompt: () => Promise<void>;
    userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
  }
}

// Sort options type
type SortOption =
  | "confidence"
  | "date"
  | "home_probability"
  | "away_probability";

const App: React.FC = () => {
  // Parley State
  const [selectedParleyPicks, setSelectedParleyPicks] = useState<
    Map<string, ParleyPickItem>
  >(new Map());
  const [isParleySlipOpen, setIsParleySlipOpen] = useState(false);

  // View State (Predictions vs Bot Dashboard)
  const [currentView, setCurrentView] = useState<"predictions" | "bot">(
    "predictions"
  );

  // PWA Install state
  const [installPrompt, setInstallPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  // ... (rest of the code follows)
  const [isInstalled, setIsInstalled] = useState(false);

  // Capture the install prompt event
  useEffect(() => {
    const handler = (e: BeforeInstallPromptEvent) => {
      e.preventDefault();
      setInstallPrompt(e);
    };
    window.addEventListener("beforeinstallprompt", handler);

    // Check if already installed
    if (window.matchMedia("(display-mode: standalone)").matches) {
      setIsInstalled(true);
    }

    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleInstallClick = async () => {
    if (!installPrompt) return;
    await installPrompt.prompt();
    const { outcome } = await installPrompt.userChoice;
    if (outcome === "accepted") {
      setIsInstalled(true);
    }
    setInstallPrompt(null);
  };

  // State and data hooks
  const {
    countries,
    loading: leaguesLoading,
    error: leaguesError,
  } = useLeagues();
  const { selectedCountry, selectedLeague, selectCountry, selectLeague } =
    useLeagueSelection();

  // Sorting state
  const [sortBy, setSortBy] = useState<SortOption>("confidence");
  // Live view state
  const [showLive, setShowLive] = useState(false);

  // Search hook
  const {
    searchQuery,
    setSearchQuery,
    searchMatches,
    loading: searchLoading,
    resetSearch,
  } = useTeamSearch();

  const {
    predictions,
    loading: predictionsLoading,
    error: predictionsError,
  } = usePredictions(selectedLeague?.id || null, 10, sortBy, true, 300000);

  // Handle sort change - this automatically triggers refetch via hook dependency
  const handleSortChange = (newSortBy: SortOption) => {
    setSortBy(newSortBy);
  };

  // Handle country selection
  const handleCountrySelect = (country: Country | null) => {
    resetSearch(); // Clear search when selecting country
    selectCountry(country);
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background: "linear-gradient(180deg, #0f172a 0%, #1e293b 100%)",
      }}
    >
      {/* Navigation */}
      <AppBar
        position="static"
        elevation={0}
        sx={{
          background: "transparent",
          borderBottom: "1px solid rgba(148, 163, 184, 0.1)",
        }}
      >
        <Toolbar>
          <SportsSoccer sx={{ mr: 2, color: "primary.main" }} />
          <Typography
            variant="h6"
            component="h1"
            sx={{ flexGrow: 1, fontWeight: 700 }}
          >
            BJJ - BetSports
          </Typography>

          {/* View Switcher */}
          <Tooltip
            title={
              currentView === "predictions"
                ? "Ir al Bot de Inversión"
                : "Ver Predicciones"
            }
          >
            <IconButton
              onClick={() =>
                setCurrentView(
                  currentView === "predictions" ? "bot" : "predictions"
                )
              }
              sx={{ color: "white", mr: 1 }}
            >
              {currentView === "predictions" ? <SmartToy /> : <Dashboard />}
            </IconButton>
          </Tooltip>

          {/* PWA Install Button */}
          {installPrompt && !isInstalled && (
            <Button
              variant="outlined"
              color="primary"
              size="small"
              startIcon={<GetApp />}
              onClick={handleInstallClick}
              sx={{ ml: 2 }}
            >
              Instalar App
            </Button>
          )}
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Container maxWidth="xl" sx={{ py: 4 }}>
        {currentView === "bot" ? (
          <BotDashboard />
        ) : (
          <>
            {/* Header */}
            <Box mb={4}>
              <Typography
                variant="h3"
                fontWeight={700}
                sx={{
                  background:
                    "linear-gradient(90deg, #6366f1 0%, #10b981 100%)",
                  backgroundClip: "text",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  mb: 1,
                }}
              >
                Predicciones de Fútbol
              </Typography>
              <Typography variant="body1" color="text.secondary" maxWidth={600}>
                Análisis estadístico de partidos de fútbol basado en datos
                históricos, distribución de Poisson y algoritmos de machine
                learning.
              </Typography>
            </Box>

            {leaguesError ? (
              <Alert
                severity="error"
                sx={{ mb: 4 }}
                action={
                  <Button
                    color="inherit"
                    size="small"
                    onClick={() => window.location.reload()}
                  >
                    Reintentar
                  </Button>
                }
              >
                Error al cargar las ligas: {leaguesError.message}. El servidor
                puede estar iniciándose.
              </Alert>
            ) : (
              <LeagueSelector
                countries={countries}
                selectedCountry={selectedCountry}
                selectedLeague={selectedLeague}
                onCountryChange={handleCountrySelect}
                onLeagueChange={selectLeague}
                loading={leaguesLoading}
                showLive={showLive}
                onLiveToggle={() => setShowLive(!showLive)}
              />
            )}

            {showLive ? (
              <Box mb={4}>
                <LiveMatchesList
                  selectedLeagueIds={selectedLeague ? [selectedLeague.id] : []}
                  selectedLeagueNames={
                    selectedLeague ? [selectedLeague.name] : []
                  }
                />
              </Box>
            ) : (
              <>
                {/* Parley Slip replaces auto ParleySection */}
                <ParleySlip
                  items={Array.from(selectedParleyPicks.values())}
                  onRemove={(id) => {
                    const newMap = new Map(selectedParleyPicks);
                    newMap.delete(id);
                    setSelectedParleyPicks(newMap);
                  }}
                  onClear={() => setSelectedParleyPicks(new Map())}
                  isOpen={isParleySlipOpen}
                  onToggle={() => setIsParleySlipOpen(!isParleySlipOpen)}
                />

                {/* Predictions Grid */}
                {(selectedLeague || searchQuery.length > 2) && (
                  <PredictionGrid
                    predictions={
                      searchQuery.length > 2 ? searchMatches : predictions
                    }
                    league={selectedLeague}
                    loading={
                      searchQuery.length > 2
                        ? searchLoading
                        : predictionsLoading
                    }
                    error={searchQuery.length > 2 ? null : predictionsError}
                    sortBy={sortBy}
                    onSortChange={handleSortChange}
                    searchQuery={searchQuery}
                    onSearchChange={setSearchQuery}
                    selectedMatchIds={Array.from(selectedParleyPicks.keys())}
                    onToggleMatchSelection={(match, pick) => {
                      const newMap = new Map(selectedParleyPicks);
                      if (newMap.has(match.match.id)) {
                        newMap.delete(match.match.id);
                      } else {
                        if (newMap.size >= 10) {
                          alert("Máximo 10 selecciones permitidas");
                          return;
                        }

                        if (pick) {
                          newMap.set(match.match.id, pick);
                          if (!isParleySlipOpen) setIsParleySlipOpen(true);
                        }
                      }
                      setSelectedParleyPicks(newMap);
                    }}
                  />
                )}
              </>
            )}
          </>
        )}

        {/* Footer */}
        <Box
          component="footer"
          sx={{
            mt: 8,
            pt: 4,
            borderTop: "1px solid rgba(148, 163, 184, 0.1)",
            textAlign: "center",
          }}
        >
          <Typography variant="body2" color="text.secondary">
            Datos de Football-Data.co.uk, API-Football, TheSportsDB, ESPN y
            Football-Data.org
          </Typography>
          <Typography
            variant="caption"
            color="text.disabled"
            display="block"
            mt={1}
          >
            © 2024 BJJ - BetSports
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

export default App;

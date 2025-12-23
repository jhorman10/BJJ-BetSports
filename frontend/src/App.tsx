/**
 * Main Application Component
 *
 * Football Betting Prediction Bot - Frontend
 * Refactored to use Zustand for state management
 */

import React, { useEffect, useMemo, useRef, useState } from "react";
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
  Snackbar,
} from "@mui/material";
import { SportsSoccer, GetApp, SmartToy, Dashboard } from "@mui/icons-material";

// Presentation Components
import LeagueSelector from "./presentation/components/LeagueSelector";
import PredictionGrid from "./presentation/components/PredictionGrid";
import LiveMatchesList from "./presentation/components/MatchDetails/LiveMatchesList";
import ParleySlip from "./presentation/components/Parley/ParleySlip";
import BotDashboard from "./presentation/components/BotDashboard/BotDashboard";
import LiveMatchDetailsModal from "./presentation/components/MatchDetails/LiveMatchDetailsModal";

// Zustand Stores
import { useUIStore } from "./application/stores/useUIStore";
import { usePredictionStore } from "./application/stores/usePredictionStore";
import { useLiveStore } from "./application/stores/useLiveStore";

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

const App: React.FC = () => {
  // UI Store
  const {
    currentView,
    setView,
    showLive,
    goalToast,
    closeGoalToast,
    showGoalToast,
  } = useUIStore();

  // Prediction Store - Fetch leagues on mount
  const { fetchLeagues, leaguesError, selectedLeague } = usePredictionStore();

  // Live Store
  const {
    matches: liveMatches,
    loading: liveLoading,
    startPolling,
    stopPolling,
  } = useLiveStore();

  // PWA Install state
  const [installPrompt, setInstallPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [isInstalled, setIsInstalled] = useState(false);

  // Goal detection ref
  const prevScoresRef = useRef<Map<string, { home: number; away: number }>>(
    new Map()
  );

  // Initialize data on mount
  useEffect(() => {
    fetchLeagues();
    startPolling(60000); // Poll every 60 seconds

    return () => {
      stopPolling();
    };
  }, [fetchLeagues, startPolling, stopPolling]);

  // Detect goals in live matches
  useEffect(() => {
    if (liveLoading) return;

    let goalDetected = false;
    let message = "";

    liveMatches.forEach((matchPred) => {
      const match = matchPred.match;
      const prev = prevScoresRef.current.get(match.id);

      if (prev) {
        if ((match.home_goals ?? 0) > prev.home) {
          goalDetected = true;
          message = `⚽ ¡GOL de ${match.home_team.name}! (${match.home_goals}-${match.away_goals})`;
        } else if ((match.away_goals ?? 0) > prev.away) {
          goalDetected = true;
          message = `⚽ ¡GOL de ${match.away_team.name}! (${match.home_goals}-${match.away_goals})`;
        }
      }

      prevScoresRef.current.set(match.id, {
        home: match.home_goals ?? 0,
        away: match.away_goals ?? 0,
      });
    });

    if (goalDetected) {
      showGoalToast(message);
    }
  }, [liveMatches, liveLoading, showGoalToast]);

  // PWA event handlers
  useEffect(() => {
    const handler = (e: BeforeInstallPromptEvent) => {
      e.preventDefault();
      setInstallPrompt(e);
    };
    window.addEventListener("beforeinstallprompt", handler);

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

  // Compute if current league has live matches
  const currentLeagueHasLiveMatches = useMemo(() => {
    if (!selectedLeague || liveMatches.length === 0) return false;

    return liveMatches.some((m) => {
      if (m.match.league?.id === selectedLeague.id) return true;
      const lName = selectedLeague.name.toLowerCase();
      const mName = (m.match.league?.name || "").toLowerCase();
      return mName.includes(lName) || lName.includes(mName);
    });
  }, [selectedLeague, liveMatches]);

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

          <Tooltip
            title={
              currentView === "predictions"
                ? "Ir al Bot de Inversión"
                : "Ver Predicciones"
            }
          >
            <IconButton
              onClick={() =>
                setView(currentView === "predictions" ? "bot" : "predictions")
              }
              sx={{ color: "white", mr: 1 }}
            >
              {currentView === "predictions" ? <SmartToy /> : <Dashboard />}
            </IconButton>
          </Tooltip>

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
                Error al cargar las ligas: {leaguesError}. El servidor puede
                estar iniciándose.
              </Alert>
            ) : (
              <LeagueSelector />
            )}

            {showLive ? (
              <Box mb={4}>
                <LiveMatchesList
                  selectedLeagueIds={
                    selectedLeague && currentLeagueHasLiveMatches
                      ? [selectedLeague.id]
                      : []
                  }
                  selectedLeagueNames={
                    selectedLeague && currentLeagueHasLiveMatches
                      ? [selectedLeague.name]
                      : []
                  }
                />
              </Box>
            ) : (
              <>
                <ParleySlip />
                <PredictionGrid />
              </>
            )}
          </>
        )}

        {/* Live Match Details Modal - Now uses internal store */}
        <React.Suspense fallback={null}>
          <LiveMatchDetailsModal />
        </React.Suspense>

        {/* Goal Notification Toast */}
        <Snackbar
          open={goalToast.open}
          autoHideDuration={5000}
          onClose={closeGoalToast}
          anchorOrigin={{ vertical: "top", horizontal: "right" }}
        >
          <Alert
            onClose={closeGoalToast}
            severity="success"
            variant="filled"
            sx={{
              width: "100%",
              bgcolor: "#10b981",
              color: "white",
              fontWeight: 700,
            }}
            icon={<SportsSoccer fontSize="inherit" />}
          >
            {goalToast.message}
          </Alert>
        </Snackbar>

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

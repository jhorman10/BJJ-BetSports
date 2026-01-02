/**
 * Main Application Component
 *
 * Football Betting Prediction Bot - Frontend
 * Refactored to use Zustand for state management
 */

import React, { useEffect, useMemo, useRef, useState } from "react";
import { Routes, Route, Link, useLocation, Navigate } from "react-router-dom";
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
import { useBotStore } from "./application/stores/useBotStore";
import OfflineIndicator from "./presentation/components/common/OfflineIndicator";
import { useOfflineStore } from "./application/stores/useOfflineStore";
import { dataReconciliationService } from "./application/services/DataReconciliationService";

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
  const { showLive, goalToast, closeGoalToast, showGoalToast } = useUIStore();

  // Prediction Store - Fetch leagues on mount
  const {
    fetchLeagues,
    leaguesError,
    selectedLeague,
    checkTrainingStatus,
    newPredictionsAvailable,
  } = usePredictionStore() as any;

  // Live Store
  const {
    matches: liveMatches,
    loading: liveLoading,
    startPolling,
    stopPolling,
  } = useLiveStore();

  const { isOnline, isBackendAvailable } = useOfflineStore();
  const { trainingStatus, fetchTrainingData } = useBotStore();

  // Only show the bot icon if training is fully completed
  const showBotIcon = trainingStatus === "COMPLETED";

  // Reconciliation: Use centralized service when connectivity restores
  useEffect(() => {
    if (isOnline && isBackendAvailable) {
      dataReconciliationService.reconcileAll();
    }
  }, [isOnline, isBackendAvailable]);

  // Auto-sync when tab becomes visible (user returns to page)
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (!document.hidden && isOnline && isBackendAvailable) {
        // Reconcile all stores when user returns to tab
        dataReconciliationService.reconcileAll();
        checkTrainingStatus();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [isOnline, isBackendAvailable, checkTrainingStatus]);

  // PWA Install state
  const [installPrompt, setInstallPrompt] =
    useState<BeforeInstallPromptEvent | null>(null);
  const [isInstalled, setIsInstalled] = useState(false);

  // --- Background Prefetching REMOVED from App.tsx - Now handled locally in PredictionGrid ---

  // Goal detection ref
  const prevScoresRef = useRef<Map<string, { home: number; away: number }>>(
    new Map()
  );

  // Initialize data on mount
  useEffect(() => {
    fetchLeagues();
    fetchTrainingData(); // Check bot/training status on startup
    checkTrainingStatus(); // Check for training updates
    startPolling(30000); // Poll every 30 seconds to match backend cache TTL

    // Poll for training updates
    const trainingInterval = setInterval(checkTrainingStatus, 60000);

    return () => {
      stopPolling();
      clearInterval(trainingInterval);
    };
  }, [
    fetchLeagues,
    fetchTrainingData,
    startPolling,
    stopPolling,
    checkTrainingStatus,
  ]);

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

  const location = useLocation();
  const isPredictions = location.pathname === "/";

  // Global Initialization Guard removed. App will load normally.

  return (
    <>
      <Box
        sx={{
          minHeight: "100vh",
          // Background handled by theme/CssBaseline
          bgcolor: "background.default",
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
            {showBotIcon && (
              <Tooltip
                title={
                  isPredictions ? "Ir al Bot de Inversión" : "Ver Predicciones"
                }
              >
                <Link
                  to={isPredictions ? "/bot" : "/"}
                  style={{ textDecoration: "none" }}
                >
                  <IconButton sx={{ color: "white", mr: 1 }}>
                    {isPredictions ? <SmartToy /> : <Dashboard />}
                  </IconButton>
                </Link>
              </Tooltip>
            )}

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
        <Container maxWidth="xl" sx={{ py: 4 }} className="page-transition">
          <Routes>
            <Route
              path="/"
              element={
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
                    <Typography
                      variant="body1"
                      color="text.secondary"
                      maxWidth={600}
                    >
                      Análisis estadístico de partidos de fútbol basado en datos
                      históricos, distribución de Poisson y algoritmos de
                      machine learning.
                    </Typography>
                  </Box>
                  {leaguesError && isBackendAvailable ? (
                    <Box>
                      <Alert
                        severity="error"
                        sx={{ mb: 2 }}
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
                        Error al cargar las ligas: {leaguesError}.
                      </Alert>
                      {/* Show Live button even when leagues fail to load */}
                      {liveMatches.length > 0 && (
                        <Button
                          variant={showLive ? "contained" : "outlined"}
                          color="error"
                          onClick={() => useUIStore.getState().toggleShowLive()}
                          sx={{ mb: 2 }}
                          startIcon={<SportsSoccer />}
                        >
                          🔴 Ver Partidos EN VIVO ({liveMatches.length})
                        </Button>
                      )}
                    </Box>
                  ) : leaguesError && !isBackendAvailable ? null : ( // If backend is down, we hide the big error alert because OfflineIndicator shows the bar
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
              }
            />
            <Route path="/bot" element={<BotDashboard />} />
            <Route path="/dashboard" element={<Navigate to="/bot" replace />} />
          </Routes>
        </Container>

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

        {/* Training Update Notification */}
        <Snackbar
          open={newPredictionsAvailable}
          anchorOrigin={{ vertical: "top", horizontal: "center" }}
        >
          <Alert
            severity="info"
            variant="filled"
            sx={{ width: "100%", bgcolor: "#3b82f6", color: "white" }}
            icon={<SmartToy fontSize="inherit" />}
          >
            ¡Nuevas predicciones disponibles! Los datos se han actualizado.
          </Alert>
        </Snackbar>

        {/* Footer */}
        <Box
          component="footer"
          sx={{
            mt: 8,
            pt: 4,
            pb: 4,
            borderTop: "1px solid rgba(148, 163, 184, 0.1)",
            textAlign: "center",
          }}
        >
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Modelos predictivos basados en datos estadísticos de alto
            rendimiento.
          </Typography>
          <Typography
            variant="caption"
            color="text.disabled"
            sx={{ display: "block", mb: 2, maxWidth: 800, mx: "auto" }}
          >
            Fuentes de datos: Football-Data.org, API-Football,
            Football-Data.co.uk, TheSportsDB, ESPN, ClubElo, Understat, FotMob,
            The Odds API, ScoreBat y OpenFootball. Las predicciones son
            probabilísticas y no garantizan resultados. Juegue con
            responsabilidad.
          </Typography>
          <Typography variant="caption" color="text.disabled" display="block">
            © 2025 BJJ - BetSports
          </Typography>
        </Box>
      </Box>

      {/* Offline Status Indicators */}
      <OfflineIndicator />
    </>
  );
};

export default App;

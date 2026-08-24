/**
 * Main Application Component
 *
 * Football Betting Prediction Bot - Frontend
 * Refactored for High Standards (SOLID/Clean Arch)
 */

import React, { useMemo } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import { Box, Typography, Alert, Button, Snackbar } from "@mui/material";
import { SportsSoccer, SmartToy } from "@mui/icons-material";

import LeagueSelector from "./presentation/components/LeagueSelector";
import PredictionGrid from "./presentation/components/PredictionGrid";
import LiveMatchesList from "./presentation/components/MatchDetails/LiveMatchesList";
import ParleySlip from "./presentation/components/Parley/ParleySlip";
import BotDashboard from "./presentation/components/BotDashboard/BotDashboard";
import LiveMatchDetailsModal from "./presentation/components/MatchDetails/LiveMatchDetailsModal";
import MainLayout from "./presentation/components/Layout/MainLayout";
import ErrorBoundary from "./presentation/components/common/ErrorBoundary";
import ParleyCalculatorPage from "./presentation/components/Parley/ParleyCalculatorPage";
import { useUIStore } from "./application/stores/useUIStore";
import { usePredictionStore } from "./application/stores/usePredictionStore";
import { useLiveStore } from "./application/stores/useLiveStore";
import { useOfflineStore } from "./application/stores/useOfflineStore";
import { useGoalDetection } from "./hooks/useGoalDetection";
import { useAppVisibility } from "./hooks/useAppVisibility";
import { useInitialization } from "./hooks/useInitialization";

const App: React.FC = () => {
  // 1. Initialization Logic (Extracted)
  useInitialization();

  // 2. Visibility & Data Sync Logic (Extracted)
  useAppVisibility();

  // 3. Goal Detection Logic (Extracted)
  const { goalToast, closeGoalToast } = useGoalDetection();

  // Stores for UI State
  const { showLive } = useUIStore();
  const leaguesError = usePredictionStore((s) => s.leaguesError);
  const selectedLeague = usePredictionStore((s) => s.selectedLeague);
  const newPredictionsAvailable = usePredictionStore((s) => s.newPredictionsAvailable);
  const { matches: liveMatches } = useLiveStore();
  const { isBackendAvailable } = useOfflineStore();

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
    <ErrorBoundary>
      <MainLayout>
      <Routes>
        <Route
          path="/"
          element={
            <>
              {/* Header */}
              <Box mb={{ xs: 2, sm: 4 }}>
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
                    lineHeight: 1.2,
                  }}
                >
                  Predicciones de Fútbol
                </Typography>
                <Typography
                  variant="body1"
                  color="text.secondary"
                  maxWidth={600}
                  sx={{ display: { xs: "none", sm: "block" } }}
                >
                  Análisis estadístico de partidos de fútbol basado en datos
                  históricos, distribución de Poisson y algoritmos de machine
                  learning.
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
              ) : leaguesError && !isBackendAvailable ? null : (
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
        <Route path="/parley-calculator" element={<ParleyCalculatorPage />} />
        <Route path="/bot" element={<BotDashboard />} />
        <Route path="/dashboard" element={<Navigate to="/bot" replace />} />
      </Routes>

      {/* Live Match Details Modal */}
      <React.Suspense fallback={null}>
        <LiveMatchDetailsModal />
      </React.Suspense>

      {/* Goal Notification Toast */}
      <Snackbar
        open={goalToast.open}
        autoHideDuration={5000}
        onClose={closeGoalToast}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
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
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
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
      </MainLayout>
    </ErrorBoundary>
  );
};

export default App;

import React, { useMemo } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Alert,
  CircularProgress,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tabs,
  Tab,
  Button,
  Snackbar,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import {
  SmartToy,
  TrendingUp,
  Assessment,
  History,
  AttachMoney,
  FilterList,
} from "@mui/icons-material";
import MatchHistoryTable from "./MatchHistoryTable";
import DashboardSkeleton from "./DashboardSkeleton";
import StatCard from "./StatCard";
import RoiEvolutionChart from "./RoiEvolutionChart";
import PicksStatsTable from "./PicksStatsTable";
import { TrainingStatus, MatchPredictionHistory } from "../../../types";
import { useBotStore } from "../../../application/stores/useBotStore";
import { useSmartPolling } from "../../../hooks/useSmartPolling";

const BotDashboard: React.FC = () => {
  // Use Bot Store for persistent state
  const {
    stats,
    lastUpdate,
    loading,
    error,
    isReconciling,
    fetchTrainingData,
    reconcile,
  } = useBotStore();

  // Smart polling: check backend every 30 seconds while tab is visible
  useSmartPolling({
    intervalMs: 30000,
    onPoll: reconcile,
    enabled: !loading, // Don't poll while training
  });

  const [startDate, setStartDate] = React.useState<string>(() => {
    const year = new Date().getFullYear();
    return `${year}-01-01`;
  });
  // Display filter date (separate from training date - allows client-side filtering)
  const [displayStartDate, setDisplayStartDate] = React.useState<string>(() => {
    const year = new Date().getFullYear();
    return `${year}-01-01`;
  });
  const [initialLoading, setInitialLoading] = React.useState(true);
  const [activeTab, setActiveTab] = React.useState(0);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const [yearMode, setYearMode] = React.useState<"current" | "previous">(
    "current"
  );

  const handleYearToggle = (
    _event: React.MouseEvent<HTMLElement>,
    newMode: "current" | "previous" | null
  ) => {
    if (newMode !== null) {
      setYearMode(newMode);
      const currentYear = new Date().getFullYear();
      const targetYear = newMode === "current" ? currentYear : currentYear - 1;

      // Siempre usar 1 de enero como fecha de inicio
      setStartDate(`${targetYear}-01-01`);
      setDisplayStartDate(`${targetYear}-01-01`);
    }
  };

  // Helper to calculate days back based on selected start date
  const getDaysBack = React.useCallback(() => {
    const start = new Date(startDate);
    const now = new Date();
    const diffTime = Math.max(0, now.getTime() - start.getTime());
    return Math.max(1, Math.ceil(diffTime / (1000 * 60 * 60 * 24)));
  }, [startDate]);

  // Client-side filtering for display metrics (allows filtering without re-training)
  const filteredStats = useMemo(() => {
    if (!stats?.match_history) return null;

    const displayDate = new Date(displayStartDate);

    // Filter match history by display date
    const filteredHistory = stats.match_history.filter(
      (m: MatchPredictionHistory) => new Date(m.match_date) >= displayDate
    );

    // Recalculate metrics from filtered data
    const matchesProcessed = filteredHistory.length;
    const correctPredictions = filteredHistory.filter(
      (m: MatchPredictionHistory) => m.was_correct
    ).length;
    const accuracy =
      matchesProcessed > 0 ? correctPredictions / matchesProcessed : 0;

    // Recalculate picks stats
    let totalBets = 0;
    let picksWon = 0;
    let picksLost = 0;

    for (const match of filteredHistory) {
      if (match.picks) {
        for (const pick of match.picks) {
          if (pick.was_correct !== undefined) {
            totalBets++;
            if (pick.was_correct) picksWon++;
            else picksLost++;
          }
        }
      }
    }

    // Estimate ROI from filtered data (simplified calculation)
    const estimatedRoi =
      totalBets > 0 ? ((picksWon * 1.8 - totalBets) / totalBets) * 100 : 0;
    const estimatedProfit = picksWon * 0.8 - picksLost;

    // Filter ROI evolution
    const filteredRoiEvolution =
      stats.roi_evolution?.filter(
        (point) => new Date(point.date) >= displayDate
      ) || [];

    return {
      ...stats,
      matches_processed: matchesProcessed,
      correct_predictions: correctPredictions,
      accuracy,
      total_bets: totalBets,
      roi: estimatedRoi,
      profit_units: estimatedProfit,
      match_history: filteredHistory,
      roi_evolution: filteredRoiEvolution,
    } as TrainingStatus;
  }, [stats, displayStartDate]);

  const clvBeatRate = useMemo(() => {
    if (!filteredStats?.match_history) return 0;
    let beat = 0;
    let total = 0;
    filteredStats.match_history.forEach((m) => {
      m.picks?.forEach((p) => {
        // Check if CLV data is available (some older picks might not have it)
        if (p.clv_beat !== undefined) {
          total++;
          if (p.clv_beat) beat++;
        }
      });
    });
    return total > 0 ? (beat / total) * 100 : 0;
  }, [filteredStats]);

  // Helper to generate mock data for local development
  const generateMockData = React.useCallback(
    async (days: number) => {
      const { mockMatchHistory } = await import("../../../mock/predictionMock");

      // Enrich mock history with picks for visualization
      const enrichedHistory = mockMatchHistory.map((m: any) => {
        const picks = m.picks ? [...m.picks] : [];

        // If legacy mock data, add winner pick
        if (picks.length === 0 && m.suggested_pick) {
          picks.push({
            market_type: "winner",
            market_label: m.suggested_pick,
            was_correct: m.pick_was_correct,
            confidence: m.confidence,
            expected_value: m.expected_value || 0,
          });
        }

        // Add random corner/card picks for visualization
        if (Math.random() > 0.6) {
          picks.push({
            market_type: Math.random() > 0.5 ? "corners_over" : "corners_under",
            market_label: "Corners Bet",
            was_correct: Math.random() > 0.4,
            confidence: 0.65,
            expected_value: 4.2,
          });
        }
        if (Math.random() > 0.6) {
          picks.push({
            market_type: Math.random() > 0.5 ? "cards_over" : "cards_under",
            market_label: "Cards Bet",
            was_correct: Math.random() > 0.4,
            confidence: 0.6,
            expected_value: 3.5,
          });
        }
        return { ...m, picks };
      });

      // Generate mock ROI evolution based on selected days
      const roiEvolution = [];
      let currentRoi = 0;
      const start = new Date(startDate);

      for (let i = 0; i < days; i++) {
        const d = new Date(start);
        d.setDate(d.getDate() + i);
        currentRoi += (Math.random() - 0.45) * 2;
        roiEvolution.push({
          date: d.toISOString().split("T")[0],
          roi: currentRoi,
        });
      }

      return {
        matches_processed: mockMatchHistory.length,
        correct_predictions: mockMatchHistory.filter((m) => m.was_correct)
          .length,
        accuracy:
          mockMatchHistory.filter((m) => m.was_correct).length /
          mockMatchHistory.length,
        total_bets: mockMatchHistory.filter((m) => m.suggested_pick).length,
        roi: currentRoi,
        profit_units: currentRoi * 2.5,
        market_stats: {},
        match_history: enrichedHistory,
        roi_evolution: roiEvolution,
      } as TrainingStatus;
    },
    [startDate]
  );

  // Run training analysis - use store's fetchTrainingData
  const runTraining = React.useCallback(
    async (forceRecalculate = false) => {
      const daysBack = getDaysBack();

      // Use store action instead of manual API calls
      await fetchTrainingData({
        forceRecalculate,
        daysBack,
        startDate,
      });

      // Fallback to mock data in DEV if needed (only if store fetch failed)
      if (import.meta.env.DEV && !stats && error) {
        const mockStats = await generateMockData(daysBack);
        // Update store with mock data
        useBotStore.getState().updateStats(mockStats);
      }
    },
    [getDaysBack, fetchTrainingData, startDate, generateMockData]
  );

  // Auto-run training when date changes
  React.useEffect(() => {
    runTraining();
  }, [runTraining]);

  // Load cached data from bot training
  React.useEffect(() => {
    // Disable skeleton after short delay
    const timer = setTimeout(() => setInitialLoading(false), 1000);
    return () => clearTimeout(timer);
  }, []);

  // Notification State
  const [notification, setNotification] = React.useState<{
    open: boolean;
    message: string;
    severity: "success" | "error" | "info";
  }>({
    open: false,
    message: "",
    severity: "info",
  });

  const handleCloseNotification = () => {
    setNotification((prev) => ({ ...prev, open: false }));
  };

  // Watch for training completion to show notification
  const prevLoadingRef = React.useRef(loading);

  React.useEffect(() => {
    if (prevLoadingRef.current && !loading) {
      // Just finished loading
      if (error) {
        setNotification({
          open: true,
          message: `Error en el entrenamiento: ${error}`,
          severity: "error",
        });
      } else if (stats) {
        setNotification({
          open: true,
          message: `¡Entrenamiento completado! Precisión: ${(
            stats.accuracy * 100
          ).toFixed(1)}% | ROI: ${stats.roi.toFixed(1)}%`,
          severity: "success",
        });
      }
    }
    prevLoadingRef.current = loading;
  }, [loading, error, stats]);

  // Calculate time since last update (direct calculation for immediate reactivity)
  const canTrain = (() => {
    if (!lastUpdate) return true;
    const hoursSinceUpdate =
      (Date.now() - lastUpdate.getTime()) / (1000 * 60 * 60);
    return hoursSinceUpdate >= 3;
  })();

  return (
    <Box sx={{ pb: 6 }}>
      {/* Show skeleton on initial load */}
      {initialLoading && <DashboardSkeleton />}

      {/* Show dashboard content after loading */}
      <Box
        sx={{
          opacity: initialLoading ? 0 : 1,
          transition: "opacity 0.5s ease-in-out",
        }}
      >
        <Box display="flex" alignItems="center" gap={2} mb={5}>
          <Box position="relative">
            {loading ? (
              <CircularProgress size={40} sx={{ color: "#fbbf24" }} />
            ) : (
              <Box>
                <Button
                  variant="contained"
                  disabled={!canTrain}
                  onClick={() => runTraining(true)}
                  startIcon={<SmartToy />}
                  sx={{
                    background: canTrain
                      ? "linear-gradient(135deg, #fbbf24 0%, #d97706 100%)"
                      : "rgba(255, 255, 255, 0.12)",
                    color: canTrain ? "#fff" : "rgba(255, 255, 255, 0.3)",
                    fontWeight: 700,
                    textTransform: "none",
                    fontSize: "0.95rem",
                    padding: "8px 24px",
                    borderRadius: "12px",
                    boxShadow: canTrain
                      ? "0 4px 15px rgba(251, 191, 36, 0.4)"
                      : "none",
                    border: canTrain
                      ? "1px solid rgba(255, 255, 255, 0.2)"
                      : "1px solid rgba(255, 255, 255, 0.05)",
                    transition: "all 0.3s ease",
                    "&:hover": {
                      background: canTrain
                        ? "linear-gradient(135deg, #f59e0b 0%, #b45309 100%)"
                        : "rgba(255, 255, 255, 0.12)",
                      transform: canTrain ? "translateY(-2px)" : "none",
                      boxShadow: canTrain
                        ? "0 8px 25px rgba(251, 191, 36, 0.5)"
                        : "none",
                    },
                    "&:disabled": {
                      background: "rgba(255, 255, 255, 0.05)",
                      color: "rgba(255, 255, 255, 0.2)",
                      border: "1px solid rgba(255, 255, 255, 0.05)",
                    },
                  }}
                >
                  {canTrain
                    ? "Recalcular Modelo IA"
                    : `Disponible en ${Math.max(
                        0,
                        3 -
                          (new Date().getTime() -
                            (lastUpdate?.getTime() || 0)) /
                            (1000 * 60 * 60)
                      ).toFixed(1)}h`}
                </Button>
              </Box>
            )}
          </Box>
          <Box>
            <Typography variant="h4" fontWeight={700} color="white">
              Estadísticas del Modelo
            </Typography>
            <Typography variant="body1" color="text.secondary" sx={{ mt: 0.5 }}>
              Rendimiento del modelo predictivo (Backtesting)
            </Typography>
          </Box>
        </Box>
        <Box ml="auto" display="flex" alignItems="center" gap={2}>
          <ToggleButtonGroup
            value={yearMode}
            exclusive
            onChange={handleYearToggle}
            size="small"
            sx={{
              height: 40,
              bgcolor: "rgba(30, 41, 59, 0.6)",
              "& .MuiToggleButton-root": {
                color: "rgba(255, 255, 255, 0.7)",
                borderColor: "rgba(148, 163, 184, 0.3)",
                textTransform: "none",
                px: 2,
                "&.Mui-selected": {
                  color: "#fbbf24",
                  bgcolor: "rgba(251, 191, 36, 0.1)",
                  "&:hover": {
                    bgcolor: "rgba(251, 191, 36, 0.2)",
                  },
                },
                "&:hover": {
                  bgcolor: "rgba(148, 163, 184, 0.1)",
                },
              },
            }}
          >
            <ToggleButton value="previous">Año Anterior</ToggleButton>
            <ToggleButton value="current">Año Actual</ToggleButton>
          </ToggleButtonGroup>

          <TextField
            label="Filtrar desde"
            type="date"
            value={displayStartDate}
            onChange={(e) => setDisplayStartDate(e.target.value)}
            InputLabelProps={{
              shrink: true,
            }}
            size="small"
            InputProps={{
              startAdornment: (
                <FilterList sx={{ mr: 1, color: "rgba(255,255,255,0.5)" }} />
              ),
            }}
            sx={{
              bgcolor: "rgba(30, 41, 59, 0.6)",
              input: { color: "white" },
              label: { color: "rgba(255, 255, 255, 0.7)" },
              "& .MuiOutlinedInput-root": {
                "& fieldset": { borderColor: "rgba(148, 163, 184, 0.3)" },
                "&:hover fieldset": { borderColor: "rgba(148, 163, 184, 0.5)" },
                "&.Mui-focused fieldset": { borderColor: "#fbbf24" },
              },
              "& .MuiSvgIcon-root": { color: "white" },
            }}
          />
        </Box>

        {loading && (
          <Alert severity="info" sx={{ mb: 4, mt: 3 }}>
            <Typography variant="body2">
              ⏳ Se están calculando los datos del modelo...
            </Typography>
          </Alert>
        )}

        {isReconciling && (
          <Alert severity="info" sx={{ mb: 4, mt: 3 }}>
            <Typography variant="body2">
              🔄 Sincronizando datos con el servidor...
            </Typography>
          </Alert>
        )}

        {lastUpdate && stats && (
          <Alert severity="success" sx={{ mb: 4, mt: 3 }}>
            <Typography variant="body2">
              <strong>✅ Última actualización:</strong>{" "}
              {lastUpdate.toLocaleDateString("es-ES", {
                day: "numeric",
                month: "long",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
                timeZone: "America/Bogota",
              })}
            </Typography>
          </Alert>
        )}

        {/* Tab Navigation */}
        <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 3 }}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            allowScrollButtonsMobile
            textColor="secondary"
            indicatorColor="secondary"
          >
            <Tab label="📊 Resumen General" />
            <Tab label="📈 Rendimiento por Mercado" />
            <Tab label="📝 Historial Completo" />
          </Tabs>
        </Box>

        {filteredStats && (
          <Box>
            {/* Tab 0: Resumen General */}
            {activeTab === 0 && (
              <Box>
                <Grid container spacing={3} sx={{ mt: 1 }}>
                  <Grid size={{ xs: 12, md: 3 }}>
                    <StatCard
                      title="ROI (Retorno de Inversión)"
                      value={`${
                        filteredStats.roi > 0 ? "+" : ""
                      }${filteredStats.roi.toFixed(1)}%`}
                      icon={<TrendingUp />}
                      color={filteredStats.roi >= 0 ? "#22c55e" : "#ef4444"}
                      subtitle="Rentabilidad sobre capital apostado"
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 3 }}>
                    <StatCard
                      title="Beneficio Neto"
                      value={`${
                        filteredStats.profit_units > 0 ? "+" : ""
                      }${filteredStats.profit_units.toFixed(1)} u`}
                      icon={<AttachMoney />}
                      color={
                        filteredStats.profit_units >= 0 ? "#fbbf24" : "#ef4444"
                      }
                      subtitle="Unidades ganadas/perdidas"
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 3 }}>
                    <StatCard
                      title="Precisión del Modelo"
                      value={`${(filteredStats.accuracy * 100).toFixed(1)}%`}
                      icon={<Assessment />}
                      color="#3b82f6"
                      subtitle={`En ${filteredStats.matches_processed} partidos analizados`}
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 3 }}>
                    <StatCard
                      title="CLV Beat Rate"
                      value={`${clvBeatRate.toFixed(1)}%`}
                      icon={<TrendingUp />}
                      color={clvBeatRate > 50 ? "#10b981" : "#f59e0b"}
                      subtitle="% Picks mejor que línea de cierre"
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 3 }}>
                    <StatCard
                      title="Picks Generados"
                      value={filteredStats.total_bets.toString()}
                      icon={<History />}
                      color="#8b5cf6"
                      subtitle="Total de picks en el período"
                    />
                  </Grid>

                  {/* ROI Chart */}
                  {filteredStats.roi_evolution &&
                    filteredStats.roi_evolution.length > 1 && (
                      <Grid size={{ xs: 12 }}>
                        <Card
                          sx={{
                            height: 400,
                            bgcolor: "rgba(30, 41, 59, 0.6)",
                            backdropFilter: "blur(10px)",
                            border: "1px solid rgba(148, 163, 184, 0.1)",
                            mt: 2,
                          }}
                        >
                          <CardContent
                            sx={{
                              p: 2,
                              "&:last-child": { pb: 2 },
                              height: "100%",
                              display: "flex",
                              flexDirection: "column",
                            }}
                          >
                            <Typography
                              variant="subtitle1"
                              fontWeight={700}
                              color="white"
                              gutterBottom
                              sx={{ mb: 1 }}
                            >
                              📈 Evolución del ROI
                            </Typography>
                            <Typography
                              variant="body2"
                              color="text.secondary"
                              sx={{ mb: 1 }}
                            >
                              Retorno de inversión acumulado basado en apuestas
                              simuladas
                            </Typography>
                            <Box flex={1} width="100%">
                              <RoiEvolutionChart
                                data={filteredStats.roi_evolution}
                              />
                            </Box>
                          </CardContent>
                        </Card>
                      </Grid>
                    )}
                </Grid>
              </Box>
            )}

            {/* Tab 1: Rendimiento por Mercado */}
            {activeTab === 1 && (
              <Box mt={2}>
                <Card
                  sx={{
                    bgcolor: "rgba(30, 41, 59, 0.6)",
                    backdropFilter: "blur(10px)",
                    border: "1px solid rgba(148, 163, 184, 0.1)",
                  }}
                >
                  <CardContent sx={{ p: 2 }}>
                    <Typography
                      variant="subtitle1"
                      fontWeight={700}
                      color="white"
                      gutterBottom
                    >
                      Estadísticas de Picks por Tipo
                    </Typography>
                    <Typography variant="body2" color="text.secondary" mb={2}>
                      Desglose de rendimiento por tipo de mercado
                    </Typography>
                    <PicksStatsTable matches={filteredStats.match_history} />
                  </CardContent>
                </Card>
              </Box>
            )}

            {/* Tab 2: Historial Completo */}
            {activeTab === 2 && (
              <Box mt={2}>
                <Typography
                  variant="h5"
                  fontWeight={700}
                  color="white"
                  gutterBottom
                  sx={{ mb: 2 }}
                >
                  Histórico de Predicciones
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={3}>
                  {filteredStats.match_history.length} partidos filtrados desde{" "}
                  {new Date(displayStartDate).toLocaleDateString("es-ES")}
                </Typography>
                <MatchHistoryTable matches={filteredStats.match_history} />
              </Box>
            )}
          </Box>
        )}
        {/* Training Notification Snackbar */}
        <Snackbar
          open={notification.open}
          autoHideDuration={6000}
          onClose={handleCloseNotification}
          anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        >
          <Alert
            onClose={handleCloseNotification}
            severity={notification.severity}
            variant="filled"
            sx={{ width: "100%", fontWeight: 600 }}
          >
            {notification.message}
          </Alert>
        </Snackbar>
      </Box>
    </Box>
  );
};

export default BotDashboard;

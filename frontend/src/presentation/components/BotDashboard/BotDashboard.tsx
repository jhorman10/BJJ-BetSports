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
  LinearProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Grid,
} from "@mui/material";
import { SmartToy, History, CheckCircle, Cancel } from "@mui/icons-material";

import { MatchPredictionHistory } from "../../../types";
import { useBotStore } from "../../../application/stores/useBotStore";
import { useTrainingJobsStore } from "../../../application/stores/useTrainingJobsStore";
import { useSmartPolling } from "../../../hooks/useSmartPolling";
import { getMarketCategory } from "../../../utils/marketUtils";
import {
  TrainingArtifactsPanel,
  TrainingControlPanel,
} from "../Training";

import MatchHistoryTable from "./MatchHistoryTable";
import StatCard from "./StatCard";

// Helper to calculate stats by market type
interface MarketStats {
  market_type: string;
  market_label: string;
  total: number;
  won: number;
  lost: number;
  accuracy: number;
}

const calculateMarketStats = (
  matches: MatchPredictionHistory[]
): MarketStats[] => {
  // Categories: Winner, Double Chance, Goals, BTTS, Corners, Cards, Handicap
  const categories: Record<
    string,
    { total: number; won: number; lost: number; label: string }
  > = {
    WINNER: { total: 0, won: 0, lost: 0, label: "Ganador del Partido (1X2)" },
    DOUBLE_CHANCE: { total: 0, won: 0, lost: 0, label: "Doble Oportunidad" },
    GOALS: { total: 0, won: 0, lost: 0, label: "Goles (Más/Menos)" },
    BTTS: { total: 0, won: 0, lost: 0, label: "Ambos Marcan" },
    CORNERS: { total: 0, won: 0, lost: 0, label: "Córners" },
    CARDS: { total: 0, won: 0, lost: 0, label: "Tarjetas" },
    HANDICAPS: { total: 0, won: 0, lost: 0, label: "Hándicap" },
  };

  for (const match of matches) {
    if (match.picks) {
      for (const pick of match.picks) {
        if (pick.was_correct === undefined) continue;

        const categoryKey = getMarketCategory(pick.market_type || "");
        if (categories[categoryKey]) {
          categories[categoryKey].total++;
          if (pick.was_correct) {
            categories[categoryKey].won++;
          } else {
            categories[categoryKey].lost++;
          }
        }
      }
    }
  }

  return Object.entries(categories)
    .reduce<{ market_type: string; market_label: string; total: number; won: number; lost: number; accuracy: number }[]>((acc, [key, value]) => {
      if (value.total > 0) {
        acc.push({
          market_type: key,
          market_label: value.label,
          total: value.total,
          won: value.won,
          lost: value.lost,
          accuracy: (value.won / value.total) * 100,
        });
      }
      return acc;
    }, [])
    .sort((a, b) => b.total - a.total);
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString("es-CO", {
    timeZone: "America/Bogota",
    day: "numeric",
    month: "short",
  });
};

const BotDashboard: React.FC = () => {
  const {
    stats,
    loading,
    error,
    trainingStatus,
    trainingMessage,
    isTrainingServiceUnavailable,
    fetchTrainingData,
    reconcile,
  } = useBotStore();
  const {
    jobs,
    capabilities,
    selectedJobId,
    selectedJobEvents,
    isLoading: trainingJobsLoading,
    error: trainingJobsError,
    createJob,
    loadCapabilities,
    loadJobs,
    refreshSelectedJob,
  } = useTrainingJobsStore();

  const selectedJob = useMemo(
    () => jobs.find((job) => job.job_id === selectedJobId) ?? null,
    [jobs, selectedJobId]
  );
  const hasActiveTrainingJob =
    selectedJob?.status === "QUEUED" ||
    selectedJob?.status === "VALIDATING" ||
    selectedJob?.status === "PREPARING_DATA" ||
    selectedJob?.status === "RUNNING";
  const capabilityReasons = capabilities?.reasons ?? [];

  React.useEffect(() => {
    void loadCapabilities().catch(() => undefined);
  }, [loadCapabilities]);

  useSmartPolling({
    intervalMs: 30000,
    onPoll: reconcile,
    enabled: !loading,
  });

  useSmartPolling({
    intervalMs: 5000,
    onPoll: async () => {
      await refreshSelectedJob();
      const refreshedJob = useTrainingJobsStore
        .getState()
        .jobs.find((job) => job.job_id === useTrainingJobsStore.getState().selectedJobId);

      if (refreshedJob?.status === "COMPLETED") {
        await fetchTrainingData();
      }
    },
    enabled: hasActiveTrainingJob,
  });

  const [displayStartDate, setDisplayStartDate] = React.useState<string>(() => {
    const now = new Date();
    const year = now.getFullYear();
    const targetYear = now.getMonth() === 0 ? year - 1 : year;
    return `${targetYear}-01-01`;
  });

  const [activeTab, setActiveTab] = React.useState(0);
  const [yearMode, setYearMode] = React.useState<"current" | "previous">(() => {
    return new Date().getMonth() === 0 ? "previous" : "current";
  });

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number): void => {
    setActiveTab(newValue);
  };

  const handleYearToggle = (
    _event: React.MouseEvent<HTMLElement>,
    newMode: "current" | "previous" | null
  ): void => {
    if (newMode !== null) {
      setYearMode(newMode);
      const currentYear = new Date().getFullYear();
      const targetYear = newMode === "current" ? currentYear : currentYear - 1;
      setDisplayStartDate(`${targetYear}-01-01`);
    }
  };

  // Filter stats by display date
  const filteredData = useMemo(() => {
    if (!stats?.match_history) return null;

    const displayDate = new Date(displayStartDate);
    const filteredHistory = stats.match_history.filter(
      (m: MatchPredictionHistory) => new Date(m.match_date) >= displayDate
    );

    // Calculate totals
    let totalPicks = 0;
    let picksWon = 0;
    let picksLost = 0;

    for (const match of filteredHistory) {
      if (match.picks) {
        for (const pick of match.picks) {
          if (pick.was_correct !== undefined) {
            totalPicks++;
            if (pick.was_correct) picksWon++;
            else picksLost++;
          }
        }
      }
    }

    const marketStats = calculateMarketStats(filteredHistory);

    return {
      match_history: filteredHistory,
      total_picks: totalPicks,
      picks_won: picksWon,
      picks_lost: picksLost,
      accuracy: totalPicks > 0 ? (picksWon / totalPicks) * 100 : 0,
      market_stats: marketStats,
    };
  }, [stats, displayStartDate]);

  // Notification state
  const [notification, setNotification] = React.useState<{
    open: boolean;
    message: string;
    severity: "success" | "error" | "info";
  }>({ open: false, message: "", severity: "info" });

  // Run training on mount
  const runTraining = React.useCallback(
    async (forceRecalculate = false) => {
      try {
        const now = new Date();
        const start = new Date(displayStartDate);
        const diffTime = Math.max(0, now.getTime() - start.getTime());
        const daysBack = Math.max(
          1,
          Math.ceil(diffTime / (1000 * 60 * 60 * 24))
        );

        if (forceRecalculate) {
          await createJob({
            recipe_id: `dashboard-${displayStartDate}`,
            name: "Manual dashboard training",
            model_key: "baseline-model",
            dataset_profile: "dashboard-manual",
            league_ids: ["E0"],
            days_back: daysBack,
            description: `Manual training requested from dashboard since ${displayStartDate}`,
          });
          setNotification({
            open: true,
            message: "Job de entrenamiento creado. Monitoreando progreso...",
            severity: "info",
          });
          return;
        }

        await Promise.all([
          fetchTrainingData({
            forceRecalculate,
            daysBack,
            startDate: displayStartDate,
          }),
          loadJobs().catch(() => undefined),
        ]);
      } catch (trainingError) {
        setNotification({
          open: true,
          message:
            trainingError instanceof Error
              ? trainingError.message
              : "No se pudo iniciar el entrenamiento.",
          severity: "error",
        });
      }
    },
    [createJob, displayStartDate, fetchTrainingData, loadJobs]
  );

  React.useEffect(() => {
    runTraining();
  }, [runTraining]);

  const handleCloseNotification = (): void => {
    setNotification((prev) => ({ ...prev, open: false }));
  };

  if (loading && !filteredData) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="400px"
      >
        <CircularProgress />
      </Box>
    );
  }

  if (error && !filteredData && !isTrainingServiceUnavailable) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box sx={{ minHeight: "100vh", p: 3 }}>
      <Box maxWidth="1400px" mx="auto">
        {/* Header */}
        <Box
          display="flex"
          alignItems="center"
          justifyContent="space-between"
          mb={4}
          flexWrap="wrap"
          gap={2}
        >
          <Box display="flex" alignItems="center" gap={2}>
            <SmartToy sx={{ fontSize: 40, color: "#fbbf24" }} />
            <Box>
              <Typography variant="h4" fontWeight={700} color="white">
                Estadísticas del Bot
              </Typography>
              <Typography variant="body1" color="text.secondary">
                Historial de picks y porcentaje de aciertos
              </Typography>
            </Box>
          </Box>

          <Box display="flex" alignItems="center" gap={2}>
            <ToggleButtonGroup
              value={yearMode}
              exclusive
              onChange={handleYearToggle}
              size="small"
              sx={{
                bgcolor: "rgba(30, 41, 59, 0.6)",
                "& .MuiToggleButton-root": {
                  color: "rgba(255, 255, 255, 0.7)",
                  textTransform: "none",
                  "&.Mui-selected": {
                    color: "#fbbf24",
                    bgcolor: "rgba(251, 191, 36, 0.1)",
                  },
                },
              }}
            >
              <ToggleButton value="previous">Año Anterior</ToggleButton>
              <ToggleButton value="current">Año Actual</ToggleButton>
            </ToggleButtonGroup>

            <TextField
              label="Desde"
              type="date"
              value={displayStartDate}
              onChange={(e) => setDisplayStartDate(e.target.value)}
              InputLabelProps={{ shrink: true }}
              size="small"
              sx={{
                "& .MuiInputBase-root": {
                  bgcolor: "rgba(30, 41, 59, 0.6)",
                  color: "white",
                },
                "& .MuiInputLabel-root": { color: "rgba(255,255,255,0.7)" },
              }}
            />
          </Box>
        </Box>

        {(trainingStatus === "IN_PROGRESS" || hasActiveTrainingJob) && (
          <Alert severity="info" sx={{ mb: 3 }}>
            <Typography variant="body2">
              ⏳ {hasActiveTrainingJob
                ? `${selectedJob?.status_message || "Entrenamiento en progreso"} (${selectedJob?.progress_percent ?? 0}%)`
                : trainingMessage || "Cargando datos..."}
            </Typography>
            <LinearProgress sx={{ mt: 1, borderRadius: 2 }} />
          </Alert>
        )}

        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid size={{ xs: 12, md: 7 }}>
            <TrainingControlPanel />
          </Grid>
          <Grid size={{ xs: 12, md: 5 }}>
            <TrainingArtifactsPanel />
          </Grid>
        </Grid>

        {selectedJob && (
          <Alert severity={selectedJob.status === "FAILED" ? "error" : "info"} sx={{ mb: 3 }}>
            <Typography variant="body2" fontWeight={700}>
              Job activo: {selectedJob.job_id}
            </Typography>
            <Typography variant="body2">
              Estado: {selectedJob.status} · Fase: {selectedJob.phase ?? "REQUESTED"} · Eventos: {selectedJobEvents.length}
            </Typography>
            <Typography variant="body2">
              {selectedJob.status_message}
            </Typography>
          </Alert>
        )}

        {trainingJobsError && !selectedJob && (
          <Alert severity="warning" sx={{ mb: 3 }}>
            {trainingJobsError}
          </Alert>
        )}

        {/* Tabs */}
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          sx={{
            mb: 3,
            "& .MuiTab-root": {
              textTransform: "none",
              fontWeight: 700,
              color: "rgba(255,255,255,0.5)",
              "&.Mui-selected": {
                color: "#fff",
                bgcolor: "rgba(59, 130, 246, 0.2)",
              },
            },
          }}
        >
          <Tab label="Resumen" />
          <Tab label="Historial" />
        </Tabs>

        {filteredData ? (
          <Box>
            {/* Tab 0: Resumen */}
            {activeTab === 0 && (
              <Box>
                {/* Summary Cards */}
                <Grid container spacing={3} sx={{ mb: 4 }}>
                  <Grid size={{ xs: 12, md: 4 }}>
                    <StatCard
                      title="Total Picks"
                      value={filteredData.total_picks.toString()}
                      icon={<History />}
                      color="#3b82f6"
                      subtitle="Picks analizados en el período"
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 4 }}>
                    <StatCard
                      title="Picks Ganados"
                      value={`${
                        filteredData.picks_won
                      } (${filteredData.accuracy.toFixed(1)}%)`}
                      icon={<CheckCircle />}
                      color="#22c55e"
                      subtitle="Picks acertados"
                    />
                  </Grid>
                  <Grid size={{ xs: 12, md: 4 }}>
                    <StatCard
                      title="Picks Perdidos"
                      value={filteredData.picks_lost.toString()}
                      icon={<Cancel />}
                      color="#ef4444"
                      subtitle="Picks fallados"
                    />
                  </Grid>
                </Grid>

                {/* Accuracy by Market Type */}
                <Card
                  sx={{
                    bgcolor: "rgba(30, 41, 59, 0.6)",
                    backdropFilter: "blur(10px)",
                    border: "1px solid rgba(148, 163, 184, 0.1)",
                  }}
                >
                  <CardContent>
                    <Typography
                      variant="h6"
                      fontWeight={700}
                      color="white"
                      gutterBottom
                    >
                      Porcentaje de Aciertos por Tipo
                    </Typography>
                    <Typography variant="body2" color="text.secondary" mb={2}>
                      Rendimiento desglosado por cada tipo de mercado
                    </Typography>

                    <TableContainer
                      component={Paper}
                      sx={{ bgcolor: "transparent" }}
                    >
                      <Table>
                        <TableHead>
                          <TableRow>
                            <TableCell
                              sx={{
                                color: "rgba(255,255,255,0.7)",
                                fontWeight: 700,
                              }}
                            >
                              Tipo de Mercado
                            </TableCell>
                            <TableCell
                              align="center"
                              sx={{
                                color: "rgba(255,255,255,0.7)",
                                fontWeight: 700,
                              }}
                            >
                              Total
                            </TableCell>
                            <TableCell
                              align="center"
                              sx={{
                                color: "rgba(255,255,255,0.7)",
                                fontWeight: 700,
                              }}
                            >
                              Ganados
                            </TableCell>
                            <TableCell
                              align="center"
                              sx={{
                                color: "rgba(255,255,255,0.7)",
                                fontWeight: 700,
                              }}
                            >
                              Perdidos
                            </TableCell>
                            <TableCell
                              align="center"
                              sx={{
                                color: "rgba(255,255,255,0.7)",
                                fontWeight: 700,
                              }}
                            >
                              % Aciertos
                            </TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {filteredData.market_stats.map((stat) => (
                            <TableRow key={stat.market_type}>
                              <TableCell sx={{ color: "white" }}>
                                {stat.market_label}
                              </TableCell>
                              <TableCell align="center" sx={{ color: "white" }}>
                                {stat.total}
                              </TableCell>
                              <TableCell
                                align="center"
                                sx={{ color: "#22c55e" }}
                              >
                                {stat.won}
                              </TableCell>
                              <TableCell
                                align="center"
                                sx={{ color: "#ef4444" }}
                              >
                                {stat.lost}
                              </TableCell>
                              <TableCell align="center">
                                <Chip
                                  label={`${stat.accuracy.toFixed(1)}%`}
                                  size="small"
                                  sx={{
                                    bgcolor:
                                      stat.accuracy >= 55
                                        ? "rgba(34, 197, 94, 0.2)"
                                        : stat.accuracy >= 45
                                        ? "rgba(251, 191, 36, 0.2)"
                                        : "rgba(239, 68, 68, 0.2)",
                                    color:
                                      stat.accuracy >= 55
                                        ? "#22c55e"
                                        : stat.accuracy >= 45
                                        ? "#fbbf24"
                                        : "#ef4444",
                                    fontWeight: 700,
                                  }}
                                />
                              </TableCell>
                            </TableRow>
                          ))}
                          {filteredData.market_stats.length === 0 && (
                            <TableRow>
                              <TableCell
                                colSpan={5}
                                align="center"
                                sx={{ color: "text.secondary" }}
                              >
                                No hay datos disponibles
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  </CardContent>
                </Card>
              </Box>
            )}

            {/* Tab 1: Historial */}
            {activeTab === 1 && (
              <Box>
                <Typography
                  variant="h5"
                  fontWeight={700}
                  color="white"
                  gutterBottom
                >
                  Historial de Picks
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={3}>
                  {filteredData.match_history.length} partidos desde{" "}
                  {formatDate(displayStartDate)}
                </Typography>
                <MatchHistoryTable matches={filteredData.match_history} />
              </Box>
            )}
          </Box>
        ) : (
          /* Empty State */
          <Box
            display="flex"
            flexDirection="column"
            alignItems="center"
            justifyContent="center"
            minHeight="400px"
            textAlign="center"
            sx={{
              bgcolor: "rgba(30, 41, 59, 0.3)",
              borderRadius: 4,
              p: 4,
              border: "1px dashed rgba(148, 163, 184, 0.3)",
            }}
          >
            <SmartToy
              sx={{ fontSize: 64, color: "rgba(255, 255, 255, 0.2)", mb: 2 }}
            />
            {isTrainingServiceUnavailable && (
              <Alert
                severity="warning"
                sx={{ mb: 3, width: "100%", maxWidth: 560, textAlign: "left" }}
              >
                <Typography variant="body2" fontWeight={700} sx={{ mb: 0.5 }}>
                  Servicio de entrenamiento no disponible
                </Typography>
                <Typography variant="body2">
                  {error ||
                    "El backend respondio 503 al iniciar el entrenamiento. Espera unos minutos y vuelve a intentar."}
                </Typography>
              </Alert>
            )}
            {!capabilities?.available && capabilityReasons.length > 0 && (
              <Alert
                severity="warning"
                sx={{ mb: 3, width: "100%", maxWidth: 560, textAlign: "left" }}
              >
                <Typography variant="body2" fontWeight={700} sx={{ mb: 0.5 }}>
                  Entrenamiento no disponible
                </Typography>
                {capabilityReasons.map((reason) => (
                  <Typography key={reason.code} variant="body2">
                    {reason.message}
                  </Typography>
                ))}
              </Alert>
            )}
            <Typography variant="h6" color="white" gutterBottom>
              No hay datos disponibles
            </Typography>
            <Typography
              variant="body1"
              color="text.secondary"
              sx={{ maxWidth: 500, mb: 3 }}
            >
              {isTrainingServiceUnavailable
                ? "El entrenamiento no pudo iniciar porque el servicio temporalmente no esta disponible."
                : "No hay datos de entrenamiento. Haz clic en el botón para iniciar."}
            </Typography>
            <Button
              variant="contained"
              onClick={() => runTraining(true)}
              startIcon={<SmartToy />}
              disabled={loading || trainingJobsLoading || hasActiveTrainingJob}
              sx={{
                background: "linear-gradient(135deg, #fbbf24 0%, #d97706 100%)",
                color: "#fff",
                fontWeight: 700,
                px: 4,
                py: 1.5,
              }}
            >
              {hasActiveTrainingJob
                ? "Entrenamiento en progreso"
                : isTrainingServiceUnavailable
                ? "Reintentar entrenamiento"
                : "Cargar Datos"}
            </Button>
          </Box>
        )}

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
          >
            {notification.message}
          </Alert>
        </Snackbar>
      </Box>
    </Box>
  );
};

export default BotDashboard;

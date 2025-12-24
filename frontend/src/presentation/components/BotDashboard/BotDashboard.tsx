import React from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Alert,
  IconButton,
  Tooltip,
  CircularProgress,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import {
  SmartToy,
  TrendingUp,
  Assessment,
  History,
  AttachMoney,
} from "@mui/icons-material";
import { api } from "../../../services/api";
import MatchHistoryTable from "./MatchHistoryTable";
import DashboardSkeleton from "./DashboardSkeleton";
import StatCard from "./StatCard";
import RoiEvolutionChart from "./RoiEvolutionChart";
import MarketPerformanceChart from "./MarketPerformanceChart";
import { TrainingStatus } from "../../../types";

const BotDashboard: React.FC = () => {
  const [loading, setLoading] = React.useState(false);
  const [stats, setStats] = React.useState<TrainingStatus | null>(null);
  const [lastUpdate, setLastUpdate] = React.useState<Date | null>(null);
  const [startDate, setStartDate] = React.useState<string>(() => {
    const year = new Date().getFullYear();
    return `${year}-01-01`;
  });
  const [initialLoading, setInitialLoading] = React.useState(true);

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
    }
  };

  // Helper to calculate days back based on selected start date
  const getDaysBack = React.useCallback(() => {
    const start = new Date(startDate);
    const now = new Date();
    const diffTime = Math.max(0, now.getTime() - start.getTime());
    return Math.max(1, Math.ceil(diffTime / (1000 * 60 * 60 * 24)));
  }, [startDate]);

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

  // Run training analysis - try cached first, then calculate if needed
  const runTraining = React.useCallback(
    async (forceRecalculate = false) => {
      setLoading(true);

      const daysBack = getDaysBack();

      try {
        // First, try to get cached results (instant)
        if (!forceRecalculate) {
          try {
            const cachedResponse = await api.get<{
              cached: boolean;
              data: TrainingStatus | null;
              last_update: string | null;
            }>("/train/cached");

            if (cachedResponse.cached && cachedResponse.data) {
              setStats(cachedResponse.data);
              setLastUpdate(
                cachedResponse.last_update
                  ? new Date(cachedResponse.last_update)
                  : new Date()
              );
              setLoading(false);
              return; // Use cached data
            }
          } catch {
            // Cache endpoint failed, continue to POST /train
            console.log("No cached training data, calculating...");
          }
        }

        // No cache or force recalculate - run full training
        const data = await api.post<TrainingStatus>("/train", {
          league_ids: ["E0", "SP1", "D1", "I1", "F1"],
          days_back: daysBack,
          start_date: startDate,
          reset_weights: false,
        });

        setStats(data);
        const now = new Date();
        setLastUpdate(now);

        // Cache the results locally too
        localStorage.setItem(
          "bot_training_stats",
          JSON.stringify({ data, timestamp: now.toISOString() })
        );

        // Show notification if supported
        if ("Notification" in window && Notification.permission === "granted") {
          new Notification("Análisis Completado", {
            body: `ROI: ${data.roi > 0 ? "+" : ""}${data.roi.toFixed(
              1
            )}% | Precisión: ${(data.accuracy * 100).toFixed(1)}%`,
            icon: "/favicon.ico",
          });
        }
      } catch (err: unknown) {
        console.error("Training error:", err);

        // Fallback to mock data in DEV if API fails
        if (import.meta.env.DEV) {
          const mockStats = await generateMockData(daysBack);
          setStats(mockStats);
          setLastUpdate(new Date());
        }
      } finally {
        setLoading(false);
      }
    },
    [getDaysBack, generateMockData, startDate]
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
              <Tooltip title="Recalcular data del modelo">
                <IconButton onClick={() => runTraining(true)} sx={{ p: 0 }}>
                  <SmartToy
                    sx={{
                      fontSize: 40,
                      color: stats ? "#fbbf24" : "rgba(255, 255, 255, 0.3)",
                      transition: "color 0.3s ease",
                    }}
                  />
                </IconButton>
              </Tooltip>
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
            label="Inicio Backtesting"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            disabled={true}
            InputLabelProps={{
              shrink: true,
            }}
            size="small"
            sx={{
              bgcolor: "rgba(30, 41, 59, 0.6)",
              input: { color: "white" },
              label: { color: "rgba(255, 255, 255, 0.7)" },
              "& .MuiOutlinedInput-root": {
                "&.Mui-disabled fieldset": {
                  borderColor: "rgba(148, 163, 184, 0.1)",
                },
                "& fieldset": { borderColor: "rgba(148, 163, 184, 0.3)" },
                "&:hover fieldset": { borderColor: "rgba(148, 163, 184, 0.5)" },
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
              })}
            </Typography>
          </Alert>
        )}

        {stats && (
          <Grid container spacing={3} sx={{ mt: 1 }}>
            <Grid size={{ xs: 12, md: 3 }}>
              <StatCard
                title="ROI (Retorno de Inversión)"
                value={`${stats.roi > 0 ? "+" : ""}${stats.roi.toFixed(1)}%`}
                icon={<TrendingUp />}
                color={stats.roi >= 0 ? "#22c55e" : "#ef4444"}
                subtitle="Rentabilidad sobre capital apostado"
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <StatCard
                title="Beneficio Neto"
                value={`${
                  stats.profit_units > 0 ? "+" : ""
                }${stats.profit_units.toFixed(1)} u`}
                icon={<AttachMoney />}
                color={stats.profit_units >= 0 ? "#fbbf24" : "#ef4444"}
                subtitle="Unidades ganadas/perdidas"
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <StatCard
                title="Precisión del Modelo"
                value={`${(stats.accuracy * 100).toFixed(1)}%`}
                icon={<Assessment />}
                color="#3b82f6"
                subtitle={`En ${stats.matches_processed} partidos analizados`}
              />
            </Grid>
            <Grid size={{ xs: 12, md: 3 }}>
              <StatCard
                title="Apuestas de Valor"
                value={stats.total_bets.toString()}
                icon={<History />}
                color="#8b5cf6"
                subtitle="Oportunidades encontradas (EV > 2%)"
              />
            </Grid>
          </Grid>
        )}

        {/* Charts Section */}
        {stats &&
          (stats as any).roi_evolution &&
          (stats as any).roi_evolution.length > 1 && (
            <Box mt={6}>
              <Grid container spacing={3}>
                {/* ROI Chart */}
                <Grid size={{ xs: 12, md: 8 }}>
                  <Card
                    sx={{
                      height: 350,
                      bgcolor: "rgba(30, 41, 59, 0.6)",
                      backdropFilter: "blur(10px)",
                      border: "1px solid rgba(148, 163, 184, 0.1)",
                    }}
                  >
                    <CardContent
                      sx={{
                        p: 1.5,
                        "&:last-child": { pb: 1.5 },
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
                        sx={{ mb: 0 }}
                      >
                        Evolución del ROI
                      </Typography>
                      <Box flex={1} width="100%" mt={0.5}>
                        <RoiEvolutionChart
                          data={(stats as any).roi_evolution}
                        />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Market Performance Chart */}
                <Grid size={{ xs: 12, md: 4 }}>
                  <Card
                    sx={{
                      height: 350,
                      bgcolor: "rgba(30, 41, 59, 0.6)",
                      backdropFilter: "blur(10px)",
                      border: "1px solid rgba(148, 163, 184, 0.1)",
                    }}
                  >
                    <CardContent
                      sx={{
                        p: 1.5,
                        "&:last-child": { pb: 1.5 },
                        height: "100%",
                      }}
                    >
                      <Typography
                        variant="subtitle1"
                        fontWeight={700}
                        color="white"
                        gutterBottom
                        sx={{ mb: 0 }}
                      >
                        Rendimiento
                      </Typography>
                      <Box sx={{ height: "calc(100% - 24px)", width: "100%" }}>
                        <MarketPerformanceChart history={stats.match_history} />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Granular Pick Efficiency Chart removed as requested */}
              </Grid>
            </Box>
          )}

        {/* Match History Section */}
        {stats && stats.match_history && stats.match_history.length > 0 && (
          <Box mt={6}>
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
              Últimos {stats.match_history.length} partidos procesados durante
              el backtesting
            </Typography>
            <MatchHistoryTable matches={stats.match_history} />
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default BotDashboard;

import React from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Alert,
  IconButton,
  Tooltip,
  CircularProgress,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
} from "@mui/material";
import {
  SmartToy,
  TrendingUp,
  Assessment,
  History,
  AttachMoney,
} from "@mui/icons-material";
import { api } from "../../services/api";
import MatchHistoryTable from "./MatchHistoryTable";
import DashboardSkeleton from "./DashboardSkeleton";
import { TrainingStatus } from "../../types";

const StatCard: React.FC<{
  title: string;
  value: string;
  icon: React.ReactNode;
  color: string;
  subtitle?: string;
}> = ({ title, value, icon, color, subtitle }) => (
  <Card
    sx={{
      height: "100%",
      bgcolor: "rgba(30, 41, 59, 0.6)",
      backdropFilter: "blur(10px)",
      border: "1px solid rgba(148, 163, 184, 0.1)",
      color: "white",
    }}
  >
    <CardContent>
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="flex-start"
      >
        <Box>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {title}
          </Typography>
          <Typography variant="h4" fontWeight={700} sx={{ color }}>
            {value}
          </Typography>
          {subtitle && (
            <Typography variant="caption" color="text.secondary">
              {subtitle}
            </Typography>
          )}
        </Box>
        <Box
          sx={{
            p: 1,
            borderRadius: 2,
            bgcolor: `${color}20`,
            color: color,
          }}
        >
          {icon}
        </Box>
      </Box>
    </CardContent>
  </Card>
);

const RoiEvolutionChart: React.FC<{
  data: { date: string; roi: number }[];
}> = ({ data }) => {
  if (!data || data.length === 0) return null;

  const rois = data.map((d) => d.roi);
  const minRoi = Math.min(0, ...rois);
  const maxRoi = Math.max(...rois);

  const range = maxRoi - minRoi;
  const padding = range === 0 ? 1 : range * 0.02;
  const yMin = minRoi - padding;
  const yMax = maxRoi + padding;
  const yRange = yMax - yMin;

  const points = data
    .map((d, i) => {
      const x = (i / (data.length - 1)) * 100;
      const y = 100 - ((d.roi - yMin) / yRange) * 100;
      return `${x},${y}`;
    })
    .join(" ");

  const areaPoints = `${points} 100,100 0,100`;
  const zeroY = 100 - ((0 - yMin) / yRange) * 100;
  const targetY = 100 - ((5 - yMin) / yRange) * 100;
  const showTarget = 5 >= yMin && 5 <= yMax;
  const lineColor = data[data.length - 1].roi >= 0 ? "#22c55e" : "#ef4444";

  // Grid lines calculation
  const gridLines = [0, 0.25, 0.5, 0.75, 1].map((p) => {
    const val = yMin + p * yRange;
    const y = 100 - p * 100;
    return { val, y };
  });

  return (
    <Box
      sx={{
        width: "100%",
        height: "100%",
        position: "relative",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Box sx={{ flex: 1, position: "relative" }}>
        {/* Y-Axis Labels */}
        {gridLines.map((line, i) => (
          <Typography
            key={i}
            variant="caption"
            sx={{
              position: "absolute",
              left: 6,
              top: `${line.y}%`,
              transform: "translateY(-50%)",
              color: "rgba(255,255,255,0.5)",
              fontSize: "0.7rem",
              textShadow: "0 1px 2px rgba(0,0,0,0.8)",
              pointerEvents: "none",
              zIndex: 1,
            }}
          >
            {line.val.toFixed(0)}%
          </Typography>
        ))}

        {showTarget && (
          <Typography
            variant="caption"
            sx={{
              position: "absolute",
              right: 0,
              top: `${targetY}%`,
              transform: "translateY(-120%)",
              color: "#fbbf24",
              fontWeight: 700,
              fontSize: "0.7rem",
              pointerEvents: "none",
              textShadow: "0 2px 4px rgba(0,0,0,0.5)",
            }}
          >
            Target 5%
          </Typography>
        )}
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          style={{ overflow: "visible" }}
        >
          <defs>
            <linearGradient id="chartGradient" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={lineColor} stopOpacity={0.2} />
              <stop offset="100%" stopColor={lineColor} stopOpacity={0} />
            </linearGradient>
          </defs>

          {/* Grid Lines */}
          {gridLines.map((line, i) => (
            <line
              key={i}
              x1="0"
              y1={line.y}
              x2="100"
              y2={line.y}
              stroke="rgba(255,255,255,0.05)"
              strokeWidth="0.5"
              vectorEffect="non-scaling-stroke"
            />
          ))}

          {/* Zero Line */}
          <line
            x1="0"
            y1={zeroY}
            x2="100"
            y2={zeroY}
            stroke="rgba(255,255,255,0.3)"
            strokeWidth="1"
            strokeDasharray="4 4"
            vectorEffect="non-scaling-stroke"
          />

          {/* Target Line (5%) */}
          {showTarget && (
            <line
              x1="0"
              y1={targetY}
              x2="100"
              y2={targetY}
              stroke="#fbbf24"
              strokeWidth="1"
              strokeDasharray="4 4"
              vectorEffect="non-scaling-stroke"
              opacity={0.7}
            />
          )}

          {/* Area Fill */}
          <polygon points={areaPoints} fill="url(#chartGradient)" />

          {/* Chart Line */}
          <polyline
            points={points}
            fill="none"
            stroke={lineColor}
            strokeWidth="2.5"
            vectorEffect="non-scaling-stroke"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        </svg>

        {/* Interactive Overlay Points for Tooltips */}
        <Box
          sx={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            pointerEvents: "none",
          }}
        >
          {data.map((d, i) => {
            const x = (i / (data.length - 1)) * 100;
            const y = 100 - ((d.roi - yMin) / yRange) * 100;
            const color = d.roi >= 0 ? "#22c55e" : "#ef4444";

            return (
              <Tooltip
                key={i}
                title={
                  <Box sx={{ textAlign: "center", p: 0.5 }}>
                    <Typography
                      variant="caption"
                      display="block"
                      color="rgba(255,255,255,0.7)"
                    >
                      {d.date}
                    </Typography>
                    <Typography variant="body2" fontWeight={700} color="white">
                      ROI: {d.roi > 0 ? "+" : ""}
                      {d.roi.toFixed(2)}%
                    </Typography>
                  </Box>
                }
                arrow
                placement="top"
              >
                <Box
                  sx={{
                    position: "absolute",
                    left: `${x}%`,
                    top: `${y}%`,
                    width: 12,
                    height: 12,
                    transform: "translate(-50%, -50%)",
                    cursor: "crosshair",
                    pointerEvents: "auto",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    "&:hover .dot": {
                      opacity: 1,
                      transform: "scale(1.5)",
                      boxShadow: `0 0 8px ${color}`,
                    },
                  }}
                >
                  <Box
                    className="dot"
                    sx={{
                      width: 6,
                      height: 6,
                      borderRadius: "50%",
                      bgcolor: color,
                      border: "1px solid white",
                      opacity: 0,
                      transition: "all 0.2s ease",
                    }}
                  />
                </Box>
              </Tooltip>
            );
          })}
        </Box>

        {/* X-Axis Labels */}
        <Box
          display="flex"
          justifyContent="space-between"
          sx={{
            position: "absolute",
            bottom: 4,
            left: 6,
            right: 6,
            pointerEvents: "none",
          }}
        >
          <Typography
            variant="caption"
            color="rgba(255,255,255,0.5)"
            sx={{ textShadow: "0 1px 2px rgba(0,0,0,0.8)" }}
          >
            {data[0].date}
          </Typography>
          <Typography
            variant="caption"
            color="rgba(255,255,255,0.5)"
            sx={{ textShadow: "0 1px 2px rgba(0,0,0,0.8)" }}
          >
            {data[data.length - 1].date}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

const MarketPerformanceChart: React.FC<{ history: any[] }> = ({ history }) => {
  const data = React.useMemo(() => {
    const stats = {
      Winner: { correct: 0, total: 0 },
      Goals: { correct: 0, total: 0 },
      Corners: { correct: 0, total: 0 },
      Cards: { correct: 0, total: 0 },
    };

    history.forEach((match) => {
      if (match.picks && Array.isArray(match.picks)) {
        match.picks.forEach((pick: any) => {
          let category: keyof typeof stats | null = null;
          const type = pick.market_type;

          if (["winner", "draw", "double_chance", "va_handicap"].includes(type))
            category = "Winner";
          else if (["goals_over", "goals_under"].includes(type))
            category = "Goals";
          else if (["corners_over", "corners_under"].includes(type))
            category = "Corners";
          else if (["cards_over", "cards_under", "red_cards"].includes(type))
            category = "Cards";

          if (category) {
            stats[category].total++;
            if (pick.was_correct) stats[category].correct++;
          }
        });
      }
    });

    return Object.entries(stats).map(([name, val]) => ({
      name,
      correct: val.correct,
      incorrect: val.total - val.correct,
      total: val.total,
      winRate: val.total > 0 ? (val.correct / val.total) * 100 : 0,
    }));
  }, [history]);

  if (data.length === 0) return null;

  const maxTotal = Math.max(...data.map((d) => d.total));

  return (
    <Box
      sx={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "space-around",
        px: 1,
        pb: 1,
      }}
    >
      {data.map((item) => {
        const correctHeight =
          maxTotal > 0 ? (item.correct / maxTotal) * 100 : 0;
        const incorrectHeight =
          maxTotal > 0 ? (item.incorrect / maxTotal) * 100 : 0;

        return (
          <Box
            key={item.name}
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              width: "20%",
            }}
          >
            <Tooltip
              title={
                <Box sx={{ textAlign: "center" }}>
                  <Typography
                    variant="caption"
                    display="block"
                    fontWeight="bold"
                  >
                    {item.name}
                  </Typography>
                  <Typography variant="body2" color="#22c55e">
                    Aciertos: {item.correct}
                  </Typography>
                  <Typography variant="body2" color="#ef4444">
                    Fallos: {item.incorrect}
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    Win Rate: {item.winRate.toFixed(1)}%
                  </Typography>
                </Box>
              }
              arrow
              placement="top"
            >
              <Box
                sx={{
                  width: "100%",
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "flex-end",
                  position: "relative",
                  cursor: "pointer",
                  minHeight: 0,
                }}
              >
                {/* Incorrect Bar (Top) */}
                {item.incorrect > 0 && (
                  <Box
                    sx={{
                      width: "100%",
                      height: `${incorrectHeight}%`,
                      bgcolor: "#ef4444",
                      opacity: 0.8,
                      borderTopLeftRadius: 4,
                      borderTopRightRadius: 4,
                      borderBottomLeftRadius: item.correct === 0 ? 4 : 0,
                      borderBottomRightRadius: item.correct === 0 ? 4 : 0,
                      transition: "all 0.3s",
                      "&:hover": { opacity: 1 },
                    }}
                  />
                )}
                {/* Correct Bar (Bottom) */}
                {item.correct > 0 && (
                  <Box
                    sx={{
                      width: "100%",
                      height: `${correctHeight}%`,
                      bgcolor: "#22c55e",
                      opacity: 0.9,
                      borderBottomLeftRadius: 4,
                      borderBottomRightRadius: 4,
                      borderTopLeftRadius: item.incorrect === 0 ? 4 : 0,
                      borderTopRightRadius: item.incorrect === 0 ? 4 : 0,
                      transition: "all 0.3s",
                      "&:hover": { opacity: 1 },
                    }}
                  />
                )}
              </Box>
            </Tooltip>
            <Typography
              variant="caption"
              sx={{
                mt: 1,
                color: "text.secondary",
                fontWeight: 600,
                fontSize: "0.7rem",
              }}
            >
              {item.name}
            </Typography>
            <Typography
              variant="caption"
              sx={{
                color: item.winRate >= 50 ? "#22c55e" : "#ef4444",
                fontWeight: 700,
              }}
            >
              {item.winRate.toFixed(0)}%
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
};

const BotDashboard: React.FC = () => {
  const [loading, setLoading] = React.useState(false);
  const [stats, setStats] = React.useState<TrainingStatus | null>(null);
  const [lastUpdate, setLastUpdate] = React.useState<Date | null>(null);
  const [startDate, setStartDate] = React.useState<string>(() => {
    const year = new Date().getFullYear();
    return `${year}-11-01`;
  });
  const [initialLoading, setInitialLoading] = React.useState(true);

  const [yearMode, setYearMode] = React.useState<"current" | "previous">(
    "current"
  );

  const handleYearToggle = (
    event: React.MouseEvent<HTMLElement>,
    newMode: "current" | "previous" | null
  ) => {
    if (newMode !== null) {
      setYearMode(newMode);
      const currentYear = new Date().getFullYear();
      const targetYear = newMode === "current" ? currentYear : currentYear - 1;
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
      const { mockMatchHistory } = await import("../../mock/predictionMock");

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

  // Run training analysis
  const runTraining = React.useCallback(async () => {
    setLoading(true);

    const daysBack = getDaysBack();

    try {
      const data = await api.post<TrainingStatus>("/train", {
        league_ids: ["E0", "SP1", "D1", "I1", "F1"],
        days_back: daysBack,
        start_date: startDate,
        reset_weights: false,
      });

      setStats(data);
      const now = new Date();
      setLastUpdate(now);

      // Cache the results
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
    } catch (err: any) {
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
  }, [getDaysBack, generateMockData, startDate]);

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
                <IconButton onClick={runTraining} sx={{ p: 0 }}>
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
            <Grid item xs={12} md={3}>
              <StatCard
                title="ROI (Retorno de Inversión)"
                value={`${stats.roi > 0 ? "+" : ""}${stats.roi.toFixed(1)}%`}
                icon={<TrendingUp />}
                color={stats.roi >= 0 ? "#22c55e" : "#ef4444"}
                subtitle="Rentabilidad sobre capital apostado"
              />
            </Grid>
            <Grid item xs={12} md={3}>
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
            <Grid item xs={12} md={3}>
              <StatCard
                title="Precisión del Modelo"
                value={`${(stats.accuracy * 100).toFixed(1)}%`}
                icon={<Assessment />}
                color="#3b82f6"
                subtitle={`En ${stats.matches_processed} partidos analizados`}
              />
            </Grid>
            <Grid item xs={12} md={3}>
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
                <Grid item xs={12} md={8}>
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
                      <Box flex={1} width="100%" mt={1}>
                        <RoiEvolutionChart
                          data={(stats as any).roi_evolution}
                        />
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>

                {/* Market Performance Chart */}
                <Grid item xs={12} md={4}>
                  <Card
                    sx={{
                      height: 350,
                      bgcolor: "rgba(30, 41, 59, 0.6)",
                      backdropFilter: "blur(10px)",
                      border: "1px solid rgba(148, 163, 184, 0.1)",
                    }}
                  >
                    <CardContent sx={{ p: 1.5, height: "100%" }}>
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

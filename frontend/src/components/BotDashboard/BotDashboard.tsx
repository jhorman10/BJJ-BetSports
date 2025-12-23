import React from "react";
import { Box, Card, CardContent, Typography, Grid, Alert } from "@mui/material";
import {
  SmartToy,
  TrendingUp,
  Assessment,
  History,
  AttachMoney,
} from "@mui/icons-material";
import { api } from "../../services/api";
import MatchHistoryTable from "./MatchHistoryTable";

export interface MatchPredictionHistory {
  match_id: string;
  home_team: string;
  away_team: string;
  match_date: string;
  predicted_winner: string;
  actual_winner: string;
  predicted_home_goals: number;
  predicted_away_goals: number;
  actual_home_goals: number;
  actual_away_goals: number;
  was_correct: boolean;
  confidence: number;
  suggested_pick?: string | null;
  pick_was_correct?: boolean | null;
  expected_value?: number | null;
}

interface TrainingStatus {
  matches_processed: number;
  correct_predictions: number;
  accuracy: number;
  total_bets: number;
  roi: number;
  profit_units: number;
  market_stats: any;
  match_history: MatchPredictionHistory[];
}

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

const BotDashboard: React.FC = () => {
  const [loading, setLoading] = React.useState(false);
  const [stats, setStats] = React.useState<TrainingStatus | null>(null);
  const [lastUpdate, setLastUpdate] = React.useState<Date | null>(null);

  // Check if we need to run training (once per day)
  const needsTraining = React.useCallback(() => {
    const cached = localStorage.getItem("bot_training_stats");
    if (!cached) return true;

    try {
      const { timestamp } = JSON.parse(cached);
      const lastRun = new Date(timestamp);
      const now = new Date();

      // Check if it's a different day
      return (
        lastRun.getDate() !== now.getDate() ||
        lastRun.getMonth() !== now.getMonth() ||
        lastRun.getFullYear() !== now.getFullYear()
      );
    } catch {
      return true;
    }
  }, []);

  // Load mock data if no stats are available (development mode only)
  React.useEffect(() => {
    if (!stats && !loading && import.meta.env.DEV) {
      // Import mock data lazily to avoid bundling in production
      import("../../mock/predictionMock").then(({ mockMatchHistory }) => {
        const mockStats = {
          matches_processed: mockMatchHistory.length,
          correct_predictions: mockMatchHistory.filter((m) => m.was_correct)
            .length,
          accuracy:
            mockMatchHistory.filter((m) => m.was_correct).length /
            mockMatchHistory.length,
          total_bets: mockMatchHistory.filter((m) => m.suggested_pick).length,
          roi: 0, // placeholder
          profit_units: 0, // placeholder
          market_stats: {},
          match_history: mockMatchHistory,
        } as any;
        setStats(mockStats);
      });
    }
  }, [stats, loading]);

  // Run training analysis
  const runTraining = React.useCallback(async () => {
    setLoading(true);

    try {
      const data = await api.post<TrainingStatus>("/train", {
        league_ids: ["E0", "SP1", "D1", "I1", "F1"],
        days_back: 365,
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
      // Error is silently caught - user will see cached data or nothing
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-run training if needed
  React.useEffect(() => {
    if (needsTraining() && !loading && !stats) {
      // Request notification permission
      if ("Notification" in window && Notification.permission === "default") {
        Notification.requestPermission();
      }
      runTraining();
    }
  }, [needsTraining, loading, stats, runTraining]);

  return (
    <Box>
      <Box display="flex" alignItems="center" gap={2} mb={4}>
        <SmartToy sx={{ fontSize: 40, color: "#fbbf24" }} />
        <Box>
          <Typography variant="h4" fontWeight={700} color="white">
            Estadísticas del Modelo
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Rendimiento del modelo predictivo (Backtesting)
          </Typography>
        </Box>
      </Box>

      {loading && (
        <Alert severity="info" sx={{ mb: 3 }}>
          <Typography variant="body2">
            ⏳ Se están calculando los datos del modelo...
          </Typography>
        </Alert>
      )}

      {lastUpdate && stats && (
        <Alert severity="success" sx={{ mb: 3 }}>
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
        <Grid container spacing={3}>
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

      {/* Match History Section */}
      {stats && stats.match_history && stats.match_history.length > 0 && (
        <Box mt={4}>
          <Typography variant="h5" fontWeight={700} color="white" gutterBottom>
            Histórico de Predicciones
          </Typography>
          <Typography variant="body2" color="text.secondary" mb={2}>
            Últimos {stats.match_history.length} partidos procesados durante el
            backtesting
          </Typography>
          <MatchHistoryTable matches={stats.match_history} />
        </Box>
      )}
    </Box>
  );
};

export default BotDashboard;

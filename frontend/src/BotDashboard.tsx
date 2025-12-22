import React, { useState } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  LinearProgress,
  Alert,
  CircularProgress,
} from "@mui/material";
import {
  SmartToy,
  TrendingUp,
  Assessment,
  History,
  PlayArrow,
  AttachMoney,
} from "@mui/icons-material";

interface TrainingStatus {
  matches_processed: number;
  correct_predictions: number;
  accuracy: number;
  total_bets: number;
  roi: number;
  profit_units: number;
  market_stats: any;
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
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<TrainingStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runSimulation = async () => {
    setLoading(true);
    setError(null);
    try {
      // Usamos fetch directo ya que api.ts no está expuesto en el contexto
      // En producción, esto debería ir en services/api.ts
      const response = await fetch("http://localhost:8000/api/v1/train", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          league_ids: ["E0", "SP1", "D1", "I1", "F1"], // Ligas Top 5
          days_back: 365, // Último año
          reset_weights: true,
        }),
      });

      if (!response.ok) throw new Error("Error en la simulación");

      const data = await response.json();
      setStats(data);
    } catch (err) {
      setError("No se pudo conectar con el servidor de Backtesting.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Box display="flex" alignItems="center" gap={2} mb={4}>
        <SmartToy sx={{ fontSize: 40, color: "#fbbf24" }} />
        <Box>
          <Typography variant="h4" fontWeight={700} color="white">
            Bot de Inversión Automática
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Simulación de estrategias y análisis de rentabilidad (Backtesting)
          </Typography>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Box mb={4}>
        <Button
          variant="contained"
          size="large"
          onClick={runSimulation}
          disabled={loading}
          startIcon={
            loading ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              <PlayArrow />
            )
          }
          sx={{
            bgcolor: "#6366f1",
            "&:hover": { bgcolor: "#4f46e5" },
            px: 4,
            py: 1.5,
          }}
        >
          {loading
            ? "Ejecutando Simulación..."
            : "Ejecutar Backtest (Último Año)"}
        </Button>
      </Box>

      {loading && (
        <Box mb={4}>
          <Typography variant="body2" color="text.secondary" mb={1}>
            Procesando partidos históricos y calculando ROI...
          </Typography>
          <LinearProgress color="secondary" />
        </Box>
      )}

      {stats && (
        <Grid container spacing={3}>
          <Grid item xs={12} md={3}>
            <StatCard
              title="ROI (Retorno de Inversión)"
              value={`${stats.roi > 0 ? "+" : ""}${stats.roi}%`}
              icon={<TrendingUp />}
              color={stats.roi >= 0 ? "#22c55e" : "#ef4444"}
              subtitle="Rentabilidad sobre capital apostado"
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <StatCard
              title="Beneficio Neto"
              value={`${stats.profit_units > 0 ? "+" : ""}${
                stats.profit_units
              } u`}
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
    </Box>
  );
};

export default BotDashboard;

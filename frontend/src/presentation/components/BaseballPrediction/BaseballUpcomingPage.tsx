import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  Alert,
  Chip,
} from "@mui/material";
import { SportsBaseball } from "@mui/icons-material";
import { api } from "../../../services/api";
import { BaseballSeries } from "../../../types";
import BaseballSeriesView from "./BaseballSeriesSelector";

const BaseballUpcomingPage: React.FC = () => {
  const [series, setSeries] = useState<BaseballSeries[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDemo, setIsDemo] = useState(false);

  useEffect(() => {
    fetchSeries();
  }, []);

  const fetchSeries = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getBaseballSeries();
      // Transform API response to match BaseballSeries type
      const seriesData: BaseballSeries[] = (response.series || []).map((s: any, idx: number) => ({
        series_id: `series_${idx}`,
        home_team: s[0]?.home_team || "",
        away_team: s[0]?.away_team || "",
        game_count: s.length,
        games: s.map((g: any) => ({
          game_id: g.game_id,
          date: g.date,
          home_team: g.home_team,
          away_team: g.away_team,
          venue: g.venue,
          day_night: g.day_night,
          home_pitcher_name: g.home_pitcher_name,
          away_pitcher_name: g.away_pitcher_name,
          home_odds: g.home_odds,
          away_odds: g.away_odds,
          prediction: g.prediction ? {
            home_win_prob: g.prediction.home_win_prob,
            away_win_prob: g.prediction.away_win_prob,
            predicted_winner: g.prediction.predicted_winner,
            confidence: g.prediction.confidence,
            key_factors: g.prediction.key_factors || [],
            markets: g.prediction.markets || [],
          } : null,
        })),
      }));
      setSeries(seriesData);
      setIsDemo(response.is_demo || false);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Error al cargar predicciones de béisbol";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" py={8}>
        <CircularProgress sx={{ color: "#6366f1" }} />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      {/* Header */}
      <Box mb={3}>
        <Box display="flex" alignItems="center" gap={1} mb={1}>
          <SportsBaseball sx={{ color: "#f59e0b", fontSize: 32 }} />
          <Typography
            variant="h3"
            fontWeight={700}
            sx={{
              background: "linear-gradient(90deg, #f59e0b 0%, #6366f1 100%)",
              backgroundClip: "text",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            Predicciones de Béisbol
          </Typography>
        </Box>
        <Typography variant="body1" color="text.secondary" maxWidth={600}>
          Análisis estadístico de partidos de MLB basado en estadísticas de pitcheo,
          bateo, forma reciente y datos históricos.
        </Typography>
        {isDemo && (
          <Chip
            label="Datos de Demostración"
            size="small"
            sx={{
              mt: 1,
              bgcolor: "rgba(245,158,11,0.15)",
              color: "#f59e0b",
              fontWeight: 600,
            }}
          />
        )}
      </Box>

      {/* Series Grid */}
      <BaseballSeriesView series={series} />
    </Box>
  );
};

export default BaseballUpcomingPage;

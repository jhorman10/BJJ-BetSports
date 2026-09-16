import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  Alert,
  Chip,
} from "@mui/material";
import { SportsBasketball } from "@mui/icons-material";

import { api } from "../../../services/api";
import {
  BasketballConference,
  BasketballGameWithPrediction,
} from "../../../types";

import BasketballTeamSelector from "./BasketballTeamSelector";
import BasketballPredictionGrid from "./BasketballPredictionGrid";

const BasketballUpcomingPage: React.FC = () => {
  const [conferences, setConferences] = useState<BasketballConference[]>([]);
  const [selectedConference, setSelectedConference] = useState<string | null>(null);
  const [games, setGames] = useState<BasketballGameWithPrediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isDemo, setIsDemo] = useState(false);

  useEffect(() => {
    fetchConferences();
  }, []);

  useEffect(() => {
    fetchGames();
  }, [selectedConference]);

  const fetchConferences = async () => {
    try {
      const response = await api.getBasketballConferences();
      setConferences(response.conferences || []);
    } catch {
      // Conferences fetch failed, will use defaults
      setConferences([
        { id: "east", name: "Eastern Conference", teams: [] },
        { id: "west", name: "Western Conference", teams: [] },
      ]);
    }
  };

  const fetchGames = async () => {
    setLoading(true);
    setError(null);
    try {
      if (selectedConference) {
        const response = await api.getBasketballPredictionsByConference(selectedConference);
        setGames(response.games || []);
      } else {
        // Fetch all games from both conferences
        const [eastRes, westRes] = await Promise.all([
          api.getBasketballPredictionsByConference("east"),
          api.getBasketballPredictionsByConference("west"),
        ]);
        setGames([...(eastRes.games || []), ...(westRes.games || [])]);
      }
      setIsDemo(false);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Error al cargar predicciones de baloncesto";
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
          <SportsBasketball sx={{ color: "#f59e0b", fontSize: 32 }} />
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
            Predicciones de Baloncesto
          </Typography>
        </Box>
        <Typography variant="body1" color="text.secondary" maxWidth={600}>
          Análisis estadístico de partidos de NBA basado en eficiencia ofensiva/defensiva,
          ritmo de juego, forma reciente y datos históricos.
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

      {/* Conference Selector */}
      <BasketballTeamSelector
        conferences={conferences}
        selectedConference={selectedConference}
        onSelect={setSelectedConference}
      />

      {/* Games Grid */}
      <BasketballPredictionGrid games={games} />
    </Box>
  );
};

export default BasketballUpcomingPage;

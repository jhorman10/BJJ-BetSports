import React, { useState } from "react";
import { Box, Typography } from "@mui/material";

import { TennisTournament } from "../../../types";

import TennisTournamentSelector from "./TennisTournamentSelector";
import TennisPredictionGrid from "./TennisPredictionGrid";

const TennisPredictionPage: React.FC = () => {
  const [selectedTournament, setSelectedTournament] =
    useState<TennisTournament | null>(null);

  return (
    <Box>
      {/* Header */}
      <Box mb={3}>
        <Typography
          variant="h3"
          fontWeight={700}
          sx={{
            background: "linear-gradient(90deg, #6366f1 0%, #10b981 100%)",
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            mb: 1,
          }}
        >
          Predicciones de Tenis
        </Typography>
        <Typography variant="body1" color="text.secondary" maxWidth={600}>
          Análisis estadístico de partidos de tenis basado en ranking, historial
          en superficie y estadísticas de jugadores.
        </Typography>
      </Box>

      {/* Tournament Selector */}
      <TennisTournamentSelector
        selectedTournament={selectedTournament}
        onSelectTournament={setSelectedTournament}
      />

      {/* Predictions Grid */}
      <TennisPredictionGrid selectedTournament={selectedTournament} />
    </Box>
  );
};

export default TennisPredictionPage;

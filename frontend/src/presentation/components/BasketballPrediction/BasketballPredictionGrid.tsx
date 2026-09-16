import React from "react";
import {
  Box,
  Typography,
  Grid,
} from "@mui/material";
import { SportsBasketball } from "@mui/icons-material";

import { BasketballGameWithPrediction } from "../../../types";

import BasketballGameCard from "./BasketballGameCard";

interface BasketballPredictionGridProps {
  games: BasketballGameWithPrediction[];
}

const BasketballPredictionGrid: React.FC<BasketballPredictionGridProps> = ({ games }) => {
  if (!games || games.length === 0) {
    return (
      <Box textAlign="center" py={8}>
        <SportsBasketball sx={{ fontSize: 48, color: "rgba(255,255,255,0.2)", mb: 2 }} />
        <Typography variant="body1" color="text.secondary">
          No hay partidos disponibles para esta conferencia
        </Typography>
      </Box>
    );
  }

  return (
    <Grid container spacing={2}>
      {games.map((game) => (
        <Grid key={game.game_id} size={{ xs: 12, sm: 6, lg: 4 }}>
          <BasketballGameCard game={game} />
        </Grid>
      ))}
    </Grid>
  );
};

export default BasketballPredictionGrid;

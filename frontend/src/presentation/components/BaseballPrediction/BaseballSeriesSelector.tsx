import React from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Grid,
  Divider,
} from "@mui/material";
import { SportsBaseball } from "@mui/icons-material";

import { BaseballSeries } from "../../../types";

import BaseballGameCard from "./BaseballGameCard";

interface BaseballSeriesViewProps {
  series: BaseballSeries[];
}

const BaseballSeriesView: React.FC<BaseballSeriesViewProps> = ({ series }) => {
  if (!series || series.length === 0) {
    return (
      <Box textAlign="center" py={8}>
        <SportsBaseball sx={{ fontSize: 48, color: "rgba(255,255,255,0.2)", mb: 2 }} />
        <Typography variant="body1" color="text.secondary">
          No hay series disponibles
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {series.map((s, idx) => (
        <Box key={s.series_id || idx} mb={4}>
          {/* Series Header */}
          <Card
            sx={{
              background: "linear-gradient(135deg, rgba(99,102,241,0.15) 0%, rgba(16,185,129,0.08) 100%)",
              border: "1px solid rgba(99,102,241,0.2)",
              borderRadius: "16px",
              mb: 2,
            }}
          >
            <CardContent sx={{ p: 2 }}>
              <Box display="flex" alignItems="center" justifyContent="space-between">
                <Box display="flex" alignItems="center" gap={1}>
                  <SportsBaseball sx={{ color: "#f59e0b" }} />
                  <Typography variant="h6" fontWeight={700} color="white">
                    {s.away_team} @ {s.home_team}
                  </Typography>
                </Box>
                <Chip
                  label={`${s.game_count} juegos`}
                  size="small"
                  sx={{
                    bgcolor: "rgba(99,102,241,0.2)",
                    color: "#a5b4fc",
                    fontWeight: 600,
                  }}
                />
              </Box>
            </CardContent>
          </Card>

          {/* Games in Series */}
          <Grid container spacing={2}>
            {s.games.map((game) => (
              <Grid key={game.game_id} size={{ xs: 12, sm: 6, lg: 4 }}>
                <BaseballGameCard game={game} />
              </Grid>
            ))}
          </Grid>

          {idx < series.length - 1 && (
            <Divider sx={{ borderColor: "rgba(255,255,255,0.06)", my: 3 }} />
          )}
        </Box>
      ))}
    </Box>
  );
};

export default BaseballSeriesView;

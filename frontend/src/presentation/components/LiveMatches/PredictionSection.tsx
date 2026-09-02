import React from "react";
import { Box, Typography, Chip, LinearProgress, Tooltip, Fade } from "@mui/material";
import { SportsScore, TrendingUp } from "@mui/icons-material";

import { LiveMatchPrediction } from "../../../types";

interface PredictionSectionProps {
  validPrediction: NonNullable<LiveMatchPrediction["prediction"]>;
  confidence: number;
  recommendation: { label: string; value: number } | null;
}

export const PredictionSection: React.FC<PredictionSectionProps> = ({
  validPrediction,
  confidence,
  recommendation,
}) => (
  <Fade in timeout={500}>
    <Box>
      <Box display="flex" alignItems="center" gap={1} mb={1}>
        <Typography variant="caption" color="text.secondary" width={24}>1</Typography>
        <Box flex={1} position="relative">
          <LinearProgress
            variant="determinate"
            value={100}
            sx={{
              height: 6,
              borderRadius: 3,
              bgcolor: "rgba(148, 163, 184, 0.15)",
              "& .MuiLinearProgress-bar": {
                background: `linear-gradient(90deg,
                  #10b981 0%,
                  #10b981 ${validPrediction.home_win_probability * 100}%,
                  #6366f1 ${validPrediction.home_win_probability * 100}%,
                  #6366f1 ${(validPrediction.home_win_probability + validPrediction.draw_probability) * 100}%,
                  #ef4444 ${(validPrediction.home_win_probability + validPrediction.draw_probability) * 100}%,
                  #ef4444 100%
                )`,
                borderRadius: 3,
              },
            }}
          />
        </Box>
        <Typography variant="caption" color="text.secondary" width={24}>2</Typography>
      </Box>
      <Box display="flex" justifyContent="space-between" mb={1}>
        <Tooltip title="Probabilidad Victoria Local">
          <Chip
            label={`1: ${(validPrediction.home_win_probability * 100).toFixed(0)}%`}
            size="small"
            sx={{
              bgcolor: recommendation?.label === "1" ? "rgba(16, 185, 129, 0.2)" : "transparent",
              border: recommendation?.label === "1" ? "1px solid #10b981" : "1px solid rgba(148, 163, 184, 0.2)",
              fontSize: "0.65rem",
              height: 20,
            }}
          />
        </Tooltip>
        <Tooltip title="Probabilidad Empate">
          <Chip
            label={`X: ${(validPrediction.draw_probability * 100).toFixed(0)}%`}
            size="small"
            sx={{
              bgcolor: recommendation?.label === "X" ? "rgba(99, 102, 241, 0.2)" : "transparent",
              border: recommendation?.label === "X" ? "1px solid #6366f1" : "1px solid rgba(148, 163, 184, 0.2)",
              fontSize: "0.65rem",
              height: 20,
            }}
          />
        </Tooltip>
        <Tooltip title="Probabilidad Victoria Visitante">
          <Chip
            label={`2: ${(validPrediction.away_win_probability * 100).toFixed(0)}%`}
            size="small"
            sx={{
              bgcolor: recommendation?.label === "2" ? "rgba(239, 68, 68, 0.2)" : "transparent",
              border: recommendation?.label === "2" ? "1px solid #ef4444" : "1px solid rgba(148, 163, 184, 0.2)",
              fontSize: "0.65rem",
              height: 20,
            }}
          />
        </Tooltip>
      </Box>
      <Box display="flex" alignItems="center" justifyContent="space-between">
        <Box display="flex" alignItems="center" gap={0.5}>
          <TrendingUp sx={{ fontSize: 14, color: "secondary.main" }} />
          <Typography variant="caption" color="text.secondary">
            Confianza: {(confidence * 100).toFixed(0)}%
          </Typography>
        </Box>
        {validPrediction.over_25_probability > 0.5 && (
          <Chip
            icon={<SportsScore sx={{ fontSize: 12 }} />}
            label={`+2.5: ${(validPrediction.over_25_probability * 100).toFixed(0)}%`}
            size="small"
            color="warning"
            variant="outlined"
            sx={{ fontSize: "0.6rem", height: 18 }}
          />
        )}
      </Box>
    </Box>
  </Fade>
);

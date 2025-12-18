/**
 * MatchCard Component
 *
 * Displays a match prediction with probability bars and recommendations.
 * Optimized with React.memo to prevent unnecessary re-renders.
 */

import React, { memo, useMemo } from "react";
import {
  Card,
  CardContent,
  Box,
  Typography,
  LinearProgress,
  Chip,
  Divider,
  Tooltip,
  Stack,
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  Schedule,
  SportsSoccer,
  Info,
} from "@mui/icons-material";
import { styled } from "@mui/material/styles";
import type { MatchPrediction } from "../../types";

interface MatchCardProps {
  matchPrediction: MatchPrediction;
  highlight?: boolean;
}

// Styled probability bar with custom colors - defined outside component
const ProbabilityBar = styled(LinearProgress)<{ barcolor: string }>(
  ({ barcolor }) => ({
    height: 10,
    borderRadius: 5,
    backgroundColor: "rgba(255, 255, 255, 0.1)",
    "& .MuiLinearProgress-bar": {
      backgroundColor: barcolor,
      borderRadius: 5,
    },
  })
);

// Helper functions - defined outside component for performance
const formatPercent = (value: number): string => `${(value * 100).toFixed(1)}%`;

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString("es-ES", {
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
};

const getProbabilityColor = (value: number): string => {
  if (value >= 0.5) return "#10b981";
  if (value >= 0.35) return "#f59e0b";
  return "#ef4444";
};

// Card styles generator
const getCardSx = (highlight?: boolean) => ({
  height: "100%",
  transition: "all 0.3s ease",
  position: "relative" as const, // Ensure valid position type
  ...(highlight
    ? {
        border: "2px solid #10b981",
        boxShadow: "0 0 20px rgba(16, 185, 129, 0.3)",
        transform: "scale(1.02)",
      }
    : {}),
  "&:hover": {
    transform: highlight ? "scale(1.03)" : "translateY(-4px)",
    boxShadow: highlight
      ? "0 0 30px rgba(16, 185, 129, 0.5)"
      : "0 12px 24px rgba(0, 0, 0, 0.3)",
  },
});

const MatchCard: React.FC<MatchCardProps> = memo(
  ({ matchPrediction, highlight }) => {
    const { match, prediction } = matchPrediction;

    const formattedDate = useMemo(
      () => formatDate(match.match_date),
      [match.match_date]
    );

    // Reuse existing useMemo logic...
    const homeGoals = useMemo(
      () => prediction.predicted_home_goals.toFixed(1),
      [prediction.predicted_home_goals]
    );

    const awayGoals = useMemo(
      () => prediction.predicted_away_goals.toFixed(1),
      [prediction.predicted_away_goals]
    );

    const homeWinPercent = useMemo(
      () => formatPercent(prediction.home_win_probability),
      [prediction.home_win_probability]
    );

    const drawPercent = useMemo(
      () => formatPercent(prediction.draw_probability),
      [prediction.draw_probability]
    );

    const awayWinPercent = useMemo(
      () => formatPercent(prediction.away_win_probability),
      [prediction.away_win_probability]
    );

    const overPercent = useMemo(
      () => formatPercent(prediction.over_25_probability),
      [prediction.over_25_probability]
    );

    const underPercent = useMemo(
      () => formatPercent(prediction.under_25_probability),
      [prediction.under_25_probability]
    );

    const confidencePercent = useMemo(
      () => formatPercent(prediction.confidence),
      [prediction.confidence]
    );

    const sourcesTooltip = useMemo(
      () => `Fuentes: ${prediction.data_sources.join(", ")}`,
      [prediction.data_sources]
    );

    return (
      <Card sx={getCardSx(highlight)}>
        {highlight && (
          <Box
            sx={{
              position: "absolute",
              top: 12,
              right: 12,
              zIndex: 1,
            }}
          >
            <Chip label="Destacado" color="success" size="small" />
          </Box>
        )}
        <CardContent>
          {/* Match Date */}
          <Box display="flex" alignItems="center" gap={1} mb={2}>
            <Schedule fontSize="small" color="secondary" />
            <Typography variant="caption" color="text.secondary">
              {formattedDate}
            </Typography>
          </Box>

          {/* Teams */}
          <Box mb={3}>
            <Stack
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              mb={1}
            >
              <Typography variant="h6" fontWeight={600} sx={{ flex: 1 }}>
                {match.home_team.name}
              </Typography>
              <Typography variant="body2" color="text.secondary" mx={1}>
                vs
              </Typography>
              <Typography
                variant="h6"
                fontWeight={600}
                sx={{ flex: 1, textAlign: "right" }}
              >
                {match.away_team.name}
              </Typography>
            </Stack>

            {/* Expected Goals */}
            <Box
              display="flex"
              justifyContent="space-between"
              alignItems="center"
              px={2}
              py={1}
              borderRadius={1}
              bgcolor="rgba(99, 102, 241, 0.1)"
            >
              <Box textAlign="center">
                <Typography variant="h5" color="primary" fontWeight={700}>
                  {homeGoals}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Goles esperados
                </Typography>
              </Box>
              <SportsSoccer sx={{ color: "text.secondary" }} />
              <Box textAlign="center">
                <Typography variant="h5" color="primary" fontWeight={700}>
                  {awayGoals}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Goles esperados
                </Typography>
              </Box>
            </Box>
          </Box>

          <Divider sx={{ mb: 2 }} />

          {/* Probabilities */}
          <Box mb={3}>
            <Typography variant="subtitle2" color="text.secondary" mb={2}>
              Probabilidades
            </Typography>

            {/* Home Win */}
            <Box mb={1.5}>
              <Box display="flex" justifyContent="space-between" mb={0.5}>
                <Typography variant="body2">Local (1)</Typography>
                <Typography variant="body2" fontWeight={600}>
                  {homeWinPercent}
                </Typography>
              </Box>
              <ProbabilityBar
                variant="determinate"
                value={prediction.home_win_probability * 100}
                barcolor={getProbabilityColor(prediction.home_win_probability)}
              />
            </Box>

            {/* Draw */}
            <Box mb={1.5}>
              <Box display="flex" justifyContent="space-between" mb={0.5}>
                <Typography variant="body2">Empate (X)</Typography>
                <Typography variant="body2" fontWeight={600}>
                  {drawPercent}
                </Typography>
              </Box>
              <ProbabilityBar
                variant="determinate"
                value={prediction.draw_probability * 100}
                barcolor={getProbabilityColor(prediction.draw_probability)}
              />
            </Box>

            {/* Away Win */}
            <Box mb={1.5}>
              <Box display="flex" justifyContent="space-between" mb={0.5}>
                <Typography variant="body2">Visitante (2)</Typography>
                <Typography variant="body2" fontWeight={600}>
                  {awayWinPercent}
                </Typography>
              </Box>
              <ProbabilityBar
                variant="determinate"
                value={prediction.away_win_probability * 100}
                barcolor={getProbabilityColor(prediction.away_win_probability)}
              />
            </Box>
          </Box>

          <Divider sx={{ mb: 2 }} />

          {/* Over/Under */}
          <Box mb={2}>
            <Typography variant="subtitle2" color="text.secondary" mb={1}>
              Más/Menos de 2.5 Goles
            </Typography>
            <Box display="flex" gap={1}>
              <Chip
                icon={<TrendingUp />}
                label={`Más: ${overPercent}`}
                color={
                  prediction.over_25_probability > 0.5 ? "success" : "default"
                }
                variant={
                  prediction.over_25_probability > 0.5 ? "filled" : "outlined"
                }
                size="small"
              />
              <Chip
                icon={<TrendingDown />}
                label={`Menos: ${underPercent}`}
                color={
                  prediction.under_25_probability > 0.5 ? "error" : "default"
                }
                variant={
                  prediction.under_25_probability > 0.5 ? "filled" : "outlined"
                }
                size="small"
              />
            </Box>
          </Box>

          <Divider sx={{ mb: 2 }} />

          {/* Recommendations */}
          <Box mb={2}>
            <Typography variant="subtitle2" color="text.secondary" mb={1}>
              Recomendación
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Chip
                label={prediction.recommended_bet}
                color="primary"
                sx={{ fontWeight: 600 }}
              />
              <Chip
                label={prediction.over_under_recommendation}
                color="secondary"
                variant="outlined"
              />
            </Stack>
          </Box>

          {/* Confidence & Sources */}
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            pt={1}
            borderTop="1px solid rgba(255, 255, 255, 0.1)"
          >
            <Tooltip title="Nivel de confianza basado en la cantidad y calidad de datos disponibles">
              <Box display="flex" alignItems="center" gap={1}>
                <Info fontSize="small" color="action" />
                <Typography variant="caption" color="text.secondary">
                  Confianza: {confidencePercent}
                </Typography>
              </Box>
            </Tooltip>
            <Tooltip title={sourcesTooltip}>
              <Chip
                label={`${prediction.data_sources.length} fuentes`}
                size="small"
                variant="outlined"
                sx={{ fontSize: "0.7rem" }}
              />
            </Tooltip>
          </Box>
        </CardContent>
      </Card>
    );
  }
);

// Display name for debugging
MatchCard.displayName = "MatchCard";

export default MatchCard;

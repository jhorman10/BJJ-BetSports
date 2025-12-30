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
  Checkbox,
  CircularProgress,
} from "@mui/material";
import {
  TrendingUp,
  TrendingDown,
  Schedule,
  SportsSoccer,
  Info,
  Diamond,
} from "@mui/icons-material";
import { styled } from "@mui/material/styles";
import type { MatchPrediction } from "../../../types";
import {
  translateRecommendedBet,
  translateOverUnder,
} from "../../../utils/translationUtils";

interface MatchCardProps {
  matchPrediction: MatchPrediction;
  highlight?: boolean;
  onClick?: () => void;
  isSelected?: boolean;
  isLoading?: boolean;
  onToggleSelection?: () => void;
}

// Styled probability bar with custom colors
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

// Helper functions
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

const getCardSx = (highlight?: boolean, clickable?: boolean) => ({
  height: "100%",
  // GPU-accelerated properties only (transform, opacity)
  transform: highlight ? "scale(1.02)" : "translateY(0)",
  transition:
    "transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
  position: "relative" as const,
  cursor: clickable ? "pointer" : "default",
  ...(highlight
    ? {
        border: "2px solid #10b981",
        boxShadow: "0 0 20px rgba(16, 185, 129, 0.3)",
      }
    : {}),
  "&:hover": {
    transform: highlight
      ? "scale(1.03)"
      : clickable
      ? "translateY(-8px) scale(1.02)"
      : "translateY(0)",
    boxShadow: highlight
      ? "0 0 30px rgba(16, 185, 129, 0.5)"
      : clickable
      ? "0 12px 24px rgba(0, 0, 0, 0.3)"
      : "none",
  },
  // Hint to browser for performance
  willChange: clickable || highlight ? "transform, box-shadow" : "auto",
});

const MatchCard: React.FC<MatchCardProps> = memo(
  ({
    matchPrediction,
    highlight,
    onClick,
    isSelected,
    isLoading,
    onToggleSelection,
  }) => {
    const { match, prediction } = matchPrediction;

    // ... useMemos ...
    const formattedDate = useMemo(
      () => formatDate(match.match_date),
      [match.match_date]
    );

    // Format stats with useMemo
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

    const isLive = ["1H", "2H", "HT", "LIVE", "ET", "P"].includes(match.status);
    const isFinished = ["FT", "AET", "PEN"].includes(match.status);

    return (
      <Card sx={getCardSx(highlight, !!onClick)} onClick={onClick}>
        {/* Selection Checkbox - Only if handler provided */}
        {onToggleSelection && (
          <Box
            sx={{
              position: "absolute",
              top: 8,
              left: 8,
              zIndex: 2,
              bgcolor: "rgba(15, 23, 42, 0.6)",
              borderRadius: "50%",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              width: 32,
              height: 32,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {isLoading ? (
              <CircularProgress size={18} sx={{ color: "#6366f1" }} />
            ) : (
              <Checkbox
                checked={!!isSelected}
                onChange={onToggleSelection}
                size="small"
                sx={{
                  color: "rgba(255,255,255,0.7)",
                  "&.Mui-checked": { color: "#6366f1" },
                  padding: 0,
                }}
              />
            )}
          </Box>
        )}

        {highlight && (
          <Box
            sx={{
              position: "absolute",
              top: 12,
              right: 12,
              zIndex: 1,
              display: "flex",
              flexDirection: "column",
              gap: 0.5,
              alignItems: "flex-end",
            }}
          >
            <Chip label="Destacado" color="success" size="small" />
          </Box>
        )}

        {/* Value Bet Badge - Always visible if value exists */}
        {prediction.is_value_bet && (
          <Box
            sx={{
              position: "absolute",
              top: highlight ? 40 : 12, // Stack below Destacado if highlighted
              right: 12,
              zIndex: 1,
            }}
          >
            <Chip
              icon={<Diamond sx={{ fontSize: "0.9rem !important" }} />}
              label={`EV +${((prediction.expected_value || 0) * 100).toFixed(
                1
              )}%`}
              size="small"
              sx={{
                bgcolor: "rgba(255, 215, 0, 0.15)",
                color: "#fbbf24",
                border: "1px solid rgba(251, 191, 36, 0.5)",
                fontWeight: "bold",
              }}
            />
          </Box>
        )}
        <CardContent>
          {/* Match Date & Status */}
          <Box
            display="flex"
            alignItems="center"
            gap={1}
            mb={2}
            pl={onToggleSelection ? 3 : 0}
          >
            <Schedule fontSize="small" color="secondary" />
            <Typography variant="caption" color="text.secondary">
              {formattedDate}
            </Typography>
            {isLive && (
              <Chip
                label="EN VIVO"
                color="error"
                size="small"
                sx={{ height: 20, fontSize: "0.625rem" }}
              />
            )}
            {isFinished && (
              <Chip
                label="FINALIZADO"
                color="default"
                size="small"
                sx={{ height: 20, fontSize: "0.625rem" }}
              />
            )}
          </Box>

          {/* Teams */}
          <Box mb={3}>
            <Stack
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              mb={1}
              spacing={1}
            >
              {/* Home Team */}
              <Box display="flex" alignItems="center" gap={1} sx={{ flex: 1 }}>
                {match.home_team.logo_url && (
                  <Box
                    component="img"
                    src={match.home_team.logo_url}
                    alt={match.home_team.name}
                    sx={{ width: 24, height: 24, objectFit: "contain" }}
                  />
                )}
                <Typography variant="h6" fontWeight={600} noWrap>
                  {match.home_team.name}
                </Typography>
              </Box>

              <Typography variant="body2" color="text.secondary" mx={1}>
                vs
              </Typography>

              {/* Away Team */}
              <Box
                display="flex"
                alignItems="center"
                justifyContent="flex-end"
                gap={1}
                sx={{ flex: 1 }}
              >
                <Typography
                  variant="h6"
                  fontWeight={600}
                  sx={{ textAlign: "right" }}
                  noWrap
                >
                  {match.away_team.name}
                </Typography>
                {match.away_team.logo_url && (
                  <Box
                    component="img"
                    src={match.away_team.logo_url}
                    alt={match.away_team.name}
                    sx={{ width: 24, height: 24, objectFit: "contain" }}
                  />
                )}
              </Box>
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
            <Stack
              direction="row"
              spacing={1}
              flexWrap="wrap"
              useFlexGap
              sx={{
                gap: 1,
                "& .MuiChip-root": {
                  maxWidth: "100%",
                  height: "auto",
                  "& .MuiChip-label": {
                    whiteSpace: "normal",
                    wordBreak: "break-word",
                    padding: "6px 10px",
                  },
                },
              }}
            >
              <Chip
                label={translateRecommendedBet(prediction.recommended_bet)}
                color="primary"
                sx={{ fontWeight: 600 }}
              />
              {/* Stake Display */}
              {(() => {
                const recPick = prediction.suggested_picks?.find(
                  (p) =>
                    p.market_label === prediction.recommended_bet ||
                    p.market_type === prediction.recommended_bet
                );
                if (recPick?.suggested_stake) {
                  return (
                    <Chip
                      label={`Stake: ${recPick.suggested_stake}u`}
                      color="warning"
                      variant="filled"
                      size="small"
                      sx={{ fontWeight: 700, color: "#000" }}
                    />
                  );
                }
                return null;
              })()}
              <Chip
                label={translateOverUnder(prediction.over_under_recommendation)}
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
            <Box display="flex" gap={1} alignItems="center">
              {prediction.data_updated_at && (
                <Tooltip
                  title={`Datos actualizados: ${new Date(
                    prediction.data_updated_at
                  ).toLocaleString()}`}
                >
                  <Typography
                    variant="caption"
                    color={
                      new Date().getTime() -
                        new Date(prediction.data_updated_at).getTime() >
                      12 * 60 * 60 * 1000
                        ? "error.main"
                        : "text.secondary"
                    }
                  >
                    ⏱ Hace{" "}
                    {Math.round(
                      (new Date().getTime() -
                        new Date(prediction.data_updated_at).getTime()) /
                        (1000 * 60 * 60)
                    )}
                    h
                  </Typography>
                </Tooltip>
              )}
              <Tooltip title={sourcesTooltip}>
                <Chip
                  label={`${prediction.data_sources.length} fuentes`}
                  size="small"
                  variant="outlined"
                  sx={{ fontSize: "0.7rem" }}
                />
              </Tooltip>
            </Box>
          </Box>
        </CardContent>
      </Card>
    );
  }
);

// Display name for debugging
MatchCard.displayName = "MatchCard";

export default MatchCard;

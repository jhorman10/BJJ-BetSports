/**
 * MatchCard Component
 *
 * Displays a match prediction with probability bars, recommendations,
 * and dynamic picks section with color-coded events.
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
import type { MatchPrediction, Match, Prediction } from "../../types";

interface MatchCardProps {
  matchPrediction: MatchPrediction;
  highlight?: boolean;
  onClick?: () => void;
}

// Pick interface for dynamic events
interface DynamicPick {
  id: string;
  event: string;
  probability: number;
  icon: string;
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

/**
 * Get pick color based on ranking (green=1st, orange=2nd, red=rest)
 */
const getPickColorByRank = (rank: number): { bg: string; border: string } => {
  switch (rank) {
    case 1:
      return { bg: "rgba(76, 175, 80, 0.15)", border: "#4caf50" };
    case 2:
      return { bg: "rgba(255, 152, 0, 0.15)", border: "#ff9800" };
    default:
      return { bg: "rgba(244, 67, 54, 0.15)", border: "#f44336" };
  }
};

/**
 * Calculate dynamic picks from match and prediction data
 */
const calculateDynamicPicks = (
  match: Match,
  prediction: Prediction
): DynamicPick[] => {
  const picks: DynamicPick[] = [];

  // Calculate total expected goals
  const totalExpectedGoals =
    prediction.predicted_home_goals + prediction.predicted_away_goals;

  // Calculate corners probability (if data available)
  const totalCorners = (match.home_corners ?? 0) + (match.away_corners ?? 0);
  if (totalCorners > 0 || totalExpectedGoals > 0) {
    // Estimated corners based on expected goals (higher goals = more corners typically)
    const expectedCorners =
      totalCorners > 0 ? totalCorners : Math.round(totalExpectedGoals * 3.5);
    const cornersProb = Math.min(0.95, 0.5 + (expectedCorners - 7) * 0.05);
    picks.push({
      id: "corners",
      event: `Total córners ${expectedCorners}+`,
      probability: Math.max(0.3, Math.min(0.95, cornersProb)),
      icon: "⚑",
    });
  }

  // Calculate yellow cards probability
  const totalYellowCards =
    (match.home_yellow_cards ?? 0) + (match.away_yellow_cards ?? 0);
  if (totalYellowCards > 0 || totalExpectedGoals > 0) {
    const expectedCards = totalYellowCards > 0 ? totalYellowCards : 3;
    const cardsProb = Math.min(0.9, 0.4 + (expectedCards - 2) * 0.1);
    picks.push({
      id: "yellow_cards",
      event: `Total amarillas ${expectedCards}+`,
      probability: Math.max(0.35, Math.min(0.9, cardsProb)),
      icon: "🟨",
    });
  }

  // Calculate red cards probability (usually low)
  const totalRedCards =
    (match.home_red_cards ?? 0) + (match.away_red_cards ?? 0);
  const redCardsProb =
    totalRedCards > 0 ? Math.min(0.5, 0.15 + totalRedCards * 0.1) : 0.12;
  picks.push({
    id: "red_cards",
    event: `Tarjeta roja ${totalRedCards > 0 ? `(${totalRedCards})` : ""}`,
    probability: redCardsProb,
    icon: "🟥",
  });

  // Total goals (over 2.5)
  picks.push({
    id: "over_goals",
    event: `Más de 2.5 goles`,
    probability: prediction.over_25_probability,
    icon: "⚽",
  });

  // Total goals (under 2.5)
  picks.push({
    id: "under_goals",
    event: `Menos de 2.5 goles`,
    probability: prediction.under_25_probability,
    icon: "🛡️",
  });

  // Winner prediction
  const winnerProb = Math.max(
    prediction.home_win_probability,
    prediction.draw_probability,
    prediction.away_win_probability
  );
  let winnerLabel = "Empate";
  if (prediction.home_win_probability === winnerProb) {
    winnerLabel = `Victoria ${match.home_team.name}`;
  } else if (prediction.away_win_probability === winnerProb) {
    winnerLabel = `Victoria ${match.away_team.name}`;
  }
  picks.push({
    id: "winner",
    event: winnerLabel,
    probability: winnerProb,
    icon: "🏆",
  });

  return picks;
};

/**
 * Assign ranking to picks based on probability
 */
const assignPickRankings = (picks: DynamicPick[]): Map<string, number> => {
  const rankings = new Map<string, number>();

  // Sort by probability descending
  const sorted = [...picks].sort((a, b) => b.probability - a.probability);

  let currentRank = 1;
  let prevProb: number | null = null;

  sorted.forEach((pick, index) => {
    // If same probability as previous, keep same rank
    if (prevProb !== null && pick.probability === prevProb) {
      rankings.set(pick.id, currentRank);
    } else {
      currentRank = index + 1;
      rankings.set(pick.id, currentRank > 2 ? 3 : currentRank);
    }
    prevProb = pick.probability;
  });

  return rankings;
};

const getCardSx = (highlight?: boolean, clickable?: boolean) => ({
  height: "100%",
  transition: "all 0.3s ease",
  position: "relative" as const,
  cursor: clickable ? "pointer" : "default",
  ...(highlight
    ? {
        border: "2px solid #10b981",
        boxShadow: "0 0 20px rgba(16, 185, 129, 0.3)",
        transform: "scale(1.02)",
      }
    : {}),
  "&:hover": {
    transform: highlight
      ? "scale(1.03)"
      : clickable
      ? "translateY(-4px)"
      : "none",
    boxShadow: highlight
      ? "0 0 30px rgba(16, 185, 129, 0.5)"
      : clickable
      ? "0 12px 24px rgba(0, 0, 0, 0.3)"
      : "none",
  },
});

const MatchCard: React.FC<MatchCardProps> = memo(
  ({ matchPrediction, highlight, onClick }) => {
    const { match, prediction } = matchPrediction;

    // Calculate dynamic picks
    const dynamicPicks = useMemo(
      () => calculateDynamicPicks(match, prediction),
      [match, prediction]
    );

    // Get pick rankings
    const pickRankings = useMemo(
      () => assignPickRankings(dynamicPicks),
      [dynamicPicks]
    );

    // Check if we have sufficient data
    const hasSufficientData = prediction.confidence > 0;

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
          {/* Match Date & Status */}
          <Box display="flex" alignItems="center" gap={1} mb={2}>
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

          {/* Dynamic Picks Section */}
          <Box mb={2}>
            <Typography variant="subtitle2" color="text.secondary" mb={1.5}>
              📊 Picks Destacados
            </Typography>
            {hasSufficientData ? (
              <Box display="flex" flexDirection="column" gap={1}>
                {dynamicPicks
                  .sort((a, b) => b.probability - a.probability)
                  .slice(0, 4) // Show top 4 picks
                  .map((pick) => {
                    const rank = pickRankings.get(pick.id) ?? 3;
                    const colors = getPickColorByRank(rank);
                    return (
                      <Box
                        key={pick.id}
                        sx={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          p: 1,
                          borderRadius: 1,
                          bgcolor: colors.bg,
                          borderLeft: `3px solid ${colors.border}`,
                        }}
                      >
                        <Typography
                          variant="body2"
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            gap: 0.5,
                          }}
                        >
                          <span>{pick.icon}</span>
                          {pick.event}
                        </Typography>
                        <Chip
                          label={formatPercent(pick.probability)}
                          size="small"
                          sx={{
                            bgcolor: colors.border,
                            color: "white",
                            fontWeight: "bold",
                            fontSize: "0.75rem",
                            height: 22,
                          }}
                        />
                      </Box>
                    );
                  })}
              </Box>
            ) : (
              <Box
                sx={{
                  p: 2,
                  textAlign: "center",
                  bgcolor: "rgba(255, 152, 0, 0.1)",
                  borderRadius: 1,
                  border: "1px dashed rgba(255, 152, 0, 0.3)",
                }}
              >
                <Typography variant="body2" color="text.secondary">
                  ⚠️ Datos insuficientes para calcular picks
                </Typography>
              </Box>
            )}
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

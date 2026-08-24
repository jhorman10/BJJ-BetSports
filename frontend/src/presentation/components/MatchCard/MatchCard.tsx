/**
 * MatchCard Component
 *
 * Displays a match prediction with probability bars and recommendations.
 * Optimized with React.memo to prevent unnecessary re-renders.
 */

import React, { memo, useState } from "react";
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
import TrendingUp from "@mui/icons-material/TrendingUp";
import TrendingDown from "@mui/icons-material/TrendingDown";
import Schedule from "@mui/icons-material/Schedule";
import SportsSoccer from "@mui/icons-material/SportsSoccer";
import Info from "@mui/icons-material/Info";
import Diamond from "@mui/icons-material/Diamond";
import PlayCircleOutline from "@mui/icons-material/PlayCircleOutline";
import AutoGraph from "@mui/icons-material/AutoGraph";
import Psychology from "@mui/icons-material/Psychology";
import { styled } from "@mui/material/styles";

import type { MatchPrediction } from "../../../types";
import {
  translateRecommendedBet,
  translateOverUnder,
} from "../../../utils/translationUtils";
import { useCacheStore } from "../../../application/stores/useCacheStore";
import { getTeamLogo, getTeamDisplayName } from "../../../utils/teamUtils";
import { TeamLogo } from "../common/TeamLogo";
import { ScoreMatrixModal } from "../MatchDetails/components/ScoreMatrixModal";

interface MatchCardProps {
  matchPrediction: MatchPrediction;
  highlight?: boolean;
  onClick?: () => void;
  isSelected?: boolean;
  isLoading?: boolean;
  onToggleSelection?: () => void;
  match?: MatchPrediction["match"];
}

// Styled probability bar with custom colors
const ProbabilityBar = styled(LinearProgress)<{ barcolor: string }>(
  ({ barcolor }) => ({
    height: 10,
    borderRadius: 5,
    backgroundColor: "rgba(255, 255, 255, 0.05)",
    "& .MuiLinearProgress-bar": {
      backgroundColor: barcolor,
      borderRadius: 5,
    },
  })
);

// Helper functions (§2.B compliant - never show "Pendiente" or zeros)
const formatPercent = (value: number, fallback: number = 0.33): string => {
  const displayValue = value > 0 ? value : fallback;
  return `${(displayValue * 100).toFixed(1)}%`;
};

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString("es-CO", {
    timeZone: "America/Bogota",
    weekday: "short",
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true,
  });
};

// CORRECCIÓN: Lógica de colores arreglada
const getProbabilityColor = (value: number): string => {
  if (value >= 0.5) return "#10b981"; // Verde para probabilidad alta (≥50%)
  if (value >= 0.35) return "#f59e0b"; // Amarillo para probabilidad media (35-49%)
  return "#ef4444"; // Rojo para probabilidad baja (<35%)
};

const getCardSx = (highlight?: boolean, clickable?: boolean): Record<string, unknown> => ({
  height: "100%",
  position: "relative" as const,
  cursor: clickable ? "pointer" : "default",

  // Premium Background & Glass
  background:
    "linear-gradient(165deg, rgba(20, 25, 35, 0.85) 0%, rgba(10, 14, 23, 0.95) 100%)",
  backdropFilter: "blur(24px)",
  borderRadius: "24px",

  // Borders
  border: highlight
    ? "1px solid rgba(59, 130, 246, 0.5)" // Blue for highlight
    : "1px solid rgba(255, 255, 255, 0.08)",

  // Shadows (Deep & Glossy)
  boxShadow: highlight
    ? "0 0 30px rgba(59, 130, 246, 0.25), inset 0 1px 0 rgba(255,255,255,0.1)"
    : "0 15px 35px -5px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255,255,255,0.1), inset 0 0 20px rgba(0,0,0,0.2)",

  // Transitions
  transition: "all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1)",

  // Hover Effects
  "&:hover": {
    transform: clickable ? "translateY(-6px) scale(1.01)" : "none",
    boxShadow: highlight
      ? "0 0 50px rgba(59, 130, 246, 0.4), inset 0 1px 0 rgba(255,255,255,0.2)"
      : "0 25px 50px -12px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255,255,255,0.2)",
    borderColor: highlight ? "#3b82f6" : "rgba(255, 255, 255, 0.2)",
  },

  // Performance hint
  willChange: clickable ? "transform, box-shadow" : "auto",
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
    const [matrixOpen, setMatrixOpen] = useState(false);

    // OPTIMIZACIÓN 2: Selector atómico para evitar re-renders innecesarios
    const prefetchMatch = useCacheStore((state) => state.prefetchMatch);

    const prefetchTimerRef = React.useRef<NodeJS.Timeout | null>(null);

    // Optimized Prefetch (Debounced)
    const handleMouseEnter = (): void => {
      if (prefetchTimerRef.current) clearTimeout(prefetchTimerRef.current);

      prefetchTimerRef.current = setTimeout(() => {
        prefetchMatch(match.id);
      }, 300); // 300ms delay to verify intent
    };

    const handleMouseLeave = (): void => {
      if (prefetchTimerRef.current) {
        clearTimeout(prefetchTimerRef.current);
        prefetchTimerRef.current = null;
      }
    };

    const handleTouchStart = (): void => {
      if (prefetchTimerRef.current) clearTimeout(prefetchTimerRef.current);
      prefetchTimerRef.current = setTimeout(() => {
        prefetchMatch(match.id);
      }, 300);
    };

    // Cleanup on unmount
    React.useEffect(() => {
      return () => {
        if (prefetchTimerRef.current) clearTimeout(prefetchTimerRef.current);
      };
    }, []);

    // OPTIMIZACIÓN 1: Eliminar useMemo para operaciones triviales
    const formattedDate = formatDate(match.match_date);
    const homeGoals = prediction.predicted_home_goals.toFixed(1);
    const awayGoals = prediction.predicted_away_goals.toFixed(1);
    const homeWinPercent = formatPercent(prediction.home_win_probability);
    const drawPercent = formatPercent(prediction.draw_probability);
    const awayWinPercent = formatPercent(prediction.away_win_probability);
    const overPercent = formatPercent(prediction.over_25_probability);
    const underPercent = formatPercent(prediction.under_25_probability);
    const confidencePercent = formatPercent(prediction.confidence);
    const sourcesTooltip = `Fuentes: ${prediction.data_sources.join(", ")}`;

    // Colores pueden mantenerse simples o con useMemo si calcular cuesta (aquí es trivial, quitamos overhead)
    const homeWinColor = getProbabilityColor(prediction.home_win_probability);
    const drawColor = getProbabilityColor(prediction.draw_probability);
    const awayWinColor = getProbabilityColor(prediction.away_win_probability);

    const isLive = ["1H", "2H", "HT", "LIVE", "ET", "P"].includes(match.status);
    const isFinished = ["FT", "AET", "PEN"].includes(match.status);

    const hasRichData = prediction.data_sources.some((s) =>
      s.includes("FotMob")
    );

    return (
      <>
        <Card
          sx={getCardSx(highlight, !!onClick)}
          onClick={onClick}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          onTouchStart={handleTouchStart}
        >
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
              width: 44,
              height: 44,
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {isLoading ? (
              <CircularProgress size={18} sx={{ color: "#3b82f6" }} />
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
              flexWrap: "wrap",
              gap: 0.5,
              alignItems: "center",
              justifyContent: "flex-end",
              maxWidth: { xs: "50%", sm: "60%" },
            }}
          >
            {/* ML Chip - appears to left of Destacado when both are present */}
            {prediction.data_sources.includes("Rigorous ML") && (
              <Tooltip title="Predicción generada por Modelo ML Riguroso">
                <Chip
                  icon={
                    <Psychology
                      sx={{
                        fontSize: "0.9rem !important",
                        color: "#ec4899 !important",
                      }}
                    />
                  }
                  label="ML"
                  size="small"
                  sx={{
                    bgcolor: "rgba(236, 72, 153, 0.15)",
                    color: "#ec4899",
                    border: "1px solid rgba(236, 72, 153, 0.3)",
                    fontWeight: 700,
                    height: 24,
                    "& .MuiChip-label": { px: 1 },
                  }}
                />
              </Tooltip>
            )}
            <Chip
              label="Destacado"
              size="small"
              sx={{
                bgcolor: "#3b82f6",
                color: "#ffffff",
                fontWeight: 700,
                boxShadow: "0 0 15px rgba(59, 130, 246, 0.6)",
                border: "1px solid rgba(255, 255, 255, 0.2)",
              }}
            />
            {prediction.highlights_url && (
              <Chip
                icon={<PlayCircleOutline />}
                label="Highlights"
                clickable
                component="a"
                 href={prediction.highlights_url}
                 target="_blank"
                 rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                size="small"
                sx={{
                  bgcolor: "rgba(59, 130, 246, 0.3)",
                  color: "#ffffff",
                  border: "1px solid rgba(59, 130, 246, 0.5)",
                  "&:hover": { bgcolor: "rgba(59, 130, 246, 0.5)" },
                  "& .MuiChip-icon": { color: "#ffffff" },
                }}
              />
            )}
          </Box>
        )}

        {/* Badge stack - non-highlight badges use flex column to avoid overlap */}
        {!highlight && (
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
            {prediction.data_sources.includes("Rigorous ML") && (
              <Tooltip title="Predicción generada por Modelo ML Riguroso">
                <Chip
                  icon={
                    <Psychology
                      sx={{
                        fontSize: "0.9rem !important",
                        color: "#ec4899 !important",
                      }}
                    />
                  }
                  label="ML"
                  size="small"
                  sx={{
                    bgcolor: "rgba(236, 72, 153, 0.15)",
                    color: "#ec4899",
                    border: "1px solid rgba(236, 72, 153, 0.3)",
                    fontWeight: 700,
                    height: 24,
                    "& .MuiChip-label": { px: 1 },
                  }}
                />
              </Tooltip>
            )}
            {hasRichData && (
              <Tooltip title="Datos enriquecidos (Córners/Tarjetas) disponibles">
                <Chip
                  icon={
                    <AutoGraph
                      sx={{
                        fontSize: "0.9rem !important",
                        color: "#a78bfa !important",
                      }}
                    />
                  }
                  label="Data+"
                  size="small"
                  sx={{
                    bgcolor: "rgba(139, 92, 246, 0.15)",
                    color: "#a78bfa",
                    border: "1px solid rgba(139, 92, 246, 0.3)",
                    fontWeight: 700,
                    height: 24,
                    "& .MuiChip-label": { px: 1 },
                  }}
                />
              </Tooltip>
            )}
            {prediction.is_value_bet && (
              <Chip
                icon={<Diamond sx={{ fontSize: "0.9rem !important" }} />}
                label={`EV +${((prediction.expected_value || 0) * 100).toFixed(
                  1
                )}%`}
                size="small"
                sx={{
                  bgcolor: "rgba(251, 191, 36, 0.2)",
                  color: "#ffffff",
                  border: "1px solid #fbbf24",
                  fontWeight: 800,
                  "& .MuiChip-icon": { color: "#fbbf24" },
                }}
              />
            )}
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
                sx={{
                  height: 20,
                  fontSize: "0.625rem",
                  color: "#ffffff",
                  fontWeight: 700,
                }}
              />
            )}
            {isFinished && (
              <Chip
                label="FINALIZADO"
                color="default"
                sx={{
                  height: 20,
                  fontSize: "0.625rem",
                  color: "#ffffff",
                  bgcolor: "rgba(255,255,255,0.2)",
                }}
              />
            )}
          </Box>

          {/* Teams */}
          <Box mb={3}>
            <Stack
              direction="row"
              alignItems="flex-start"
              justifyContent="space-between"
              mb={1}
              spacing={1}
            >
              {/* Home Team */}
              <Box
                display="flex"
                flexDirection="column"
                alignItems="center"
                sx={{ flex: 1, minWidth: 0 }}
              >
                <TeamLogo
                  src={getTeamLogo(match.home_team)}
                alt={getTeamDisplayName(match.home_team)}
                  width={{ xs: 36, sm: 44, md: 48 }}
                  height={{ xs: 36, sm: 44, md: 48 }}
                  sx={{ mb: 0.5 }}
                />
                <Typography
                  variant="body2"
                  fontWeight={600}
                  sx={{
                    textAlign: "center",
                    fontSize: { xs: "0.75rem", sm: "0.875rem" },
                    lineHeight: 1.2,
                    wordBreak: "break-word",
                  }}
                >
                   {getTeamDisplayName(match.home_team)}
                </Typography>
                {match.home_spi && (
                  <Tooltip title="Soccer Power Index (SPI)">
                    <Typography
                      variant="caption"
                      sx={{ color: "text.secondary", fontSize: "0.6rem" }}
                    >
                      SPI: {match.home_spi.toFixed(1)}
                    </Typography>
                  </Tooltip>
                )}
              </Box>

              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ alignSelf: "center", mx: 0.5 }}
              >
                vs
              </Typography>

              {/* Away Team */}
              <Box
                display="flex"
                flexDirection="column"
                alignItems="center"
                sx={{ flex: 1, minWidth: 0 }}
              >
                <TeamLogo
                  src={getTeamLogo(match.away_team)}
                alt={getTeamDisplayName(match.away_team)}
                  width={{ xs: 36, sm: 44, md: 48 }}
                  height={{ xs: 36, sm: 44, md: 48 }}
                  sx={{ mb: 0.5 }}
                />
                <Typography
                  variant="body2"
                  fontWeight={600}
                  sx={{
                    textAlign: "center",
                    fontSize: { xs: "0.75rem", sm: "0.875rem" },
                    lineHeight: 1.2,
                    wordBreak: "break-word",
                  }}
                >
                   {getTeamDisplayName(match.away_team)}
                </Typography>
                {match.away_spi && (
                  <Tooltip title="Soccer Power Index (SPI)">
                    <Typography
                      variant="caption"
                      sx={{ color: "text.secondary", fontSize: "0.6rem" }}
                    >
                      SPI: {match.away_spi.toFixed(1)}
                    </Typography>
                  </Tooltip>
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
              sx={{ bgcolor: "rgba(59, 130, 246, 0.1)" }} // Neon Blue background
            >
              <Box textAlign="center">
                <Typography
                  variant="h5"
                  color="primary"
                  fontWeight={800}
                  sx={{ textShadow: "0 0 10px rgba(59, 130, 246, 0.5)" }}
                >
                  {homeGoals}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{ color: "rgba(255,255,255,0.7)" }}
                >
                  Goles esperados
                </Typography>
              </Box>
              <SportsSoccer sx={{ color: "text.secondary" }} />
              <Box textAlign="center">
                <Typography
                  variant="h5"
                  color="primary"
                  fontWeight={800}
                  sx={{ textShadow: "0 0 10px rgba(59, 130, 246, 0.5)" }}
                >
                  {awayGoals}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{ color: "rgba(255,255,255,0.7)" }}
                >
                   Goles esperados
                 </Typography>
               </Box>
             </Box>
           </Box>

           {/* Marcador Tentativo */}
           {prediction.score_probabilities &&
             prediction.score_probabilities.length > 0 && (
               <Box
                 mt={2}
                 p={1.5}
                 sx={{
                   bgcolor: "rgba(59, 130, 246, 0.08)",
                   border: "1px solid rgba(59, 130, 246, 0.25)",
                   borderRadius: 1,
                   cursor: "pointer",
                 }}
                 onClick={(e) => {
                   e.stopPropagation();
                   setMatrixOpen(true);
                 }}
               >
                 <Box display="flex" alignItems="center" gap={1} mb={1}>
                   <Typography variant="caption" color="primary.main" fontWeight={700}>
                     🎲 Marcador Tentativo
                   </Typography>
                   {prediction.score_confidence_tier && (
                     <Chip
                       label={prediction.score_confidence_tier}
                       size="small"
                       color={
                         prediction.score_confidence_tier === "Alta"
                           ? "success"
                           : prediction.score_confidence_tier === "Media"
                             ? "warning"
                             : prediction.score_confidence_tier === "Baja"
                               ? "error"
                               : "default"
                       }
                       sx={{ fontSize: "0.65rem", height: 20 }}
                     />
                   )}
                   <Typography
                     variant="caption"
                     sx={{ ml: "auto", color: "text.secondary", fontSize: "0.65rem" }}
                   >
                     Ver matriz →
                   </Typography>
                 </Box>
                 <Box display="flex" flexWrap="wrap" gap={0.8}>
                   {prediction.score_probabilities
                     .slice(0, 5)
                      .map((score, index) => (
                        <Chip
                          key={`${score.home_goals}-${score.away_goals}`}
                         label={`${score.home_goals}-${score.away_goals} ${(score.probability * 100).toFixed(1)}%`}
                         variant={index === 0 ? "filled" : "outlined"}
                         size="small"
                         sx={{
                           borderColor: "rgba(59, 130, 246, 0.3)",
                           color: index === 0 ? "#ffffff" : "text.primary",
                           fontWeight: index === 0 ? 700 : 400,
                           bgcolor: index === 0 ? "primary.main" : "transparent",
                           fontSize: "0.7rem",
                           height: 24,
                           ...(index === 0 && {
                             boxShadow: "0 0 8px rgba(59, 130, 246, 0.4)",
                           }),
                         }}
                       />
                     ))}
                 </Box>
               </Box>
             )}

           <Divider sx={{ mb: 2 }} />

          {/* Probabilities - CORRECCIÓN: Usar colores memoizados */}
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
                barcolor={homeWinColor}
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
                barcolor={drawColor}
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
                barcolor={awayWinColor}
              />
            </Box>

            {/* Real-time Odds comparison if available - REMOVED per user request */}
          </Box>

          <Divider sx={{ mb: 2 }} />

          {/* Over/Under - CORRECCIÓN: Lógica de colores mejorada */}
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
                sx={{
                  color: "#ffffff", // White text enforced
                  fontWeight: 700,
                  bgcolor:
                    prediction.over_25_probability > 0.5
                      ? "success.main"
                      : "transparent",
                  borderColor: "success.main",
                  ...(prediction.over_25_probability > 0.5 && {
                    boxShadow: "0 0 10px rgba(16, 185, 129, 0.4)",
                  }),
                }}
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
                sx={{
                  color: "#ffffff", // White text enforced
                  fontWeight: 700,
                  bgcolor:
                    prediction.under_25_probability > 0.5
                      ? "error.main"
                      : "transparent",
                  borderColor: "error.main",
                  ...(prediction.under_25_probability > 0.5 && {
                    boxShadow: "0 0 10px rgba(239, 68, 68, 0.4)",
                  }),
                }}
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
                sx={{
                  fontWeight: 800,
                  color: "#ffffff",
                  bgcolor: "rgba(59, 130, 246, 0.8)",
                  boxShadow: "0 0 10px rgba(59, 130, 246, 0.4)",
                  border: "1px solid #3b82f6",
                }}
              />
              {/* Stake Display */}
              {(() => {
                const recPick = (prediction.suggested_picks || []).find(
                  (p) =>
                    p.market_label === prediction.recommended_bet ||
                    p.market_type === prediction.recommended_bet
                );
                if (recPick?.suggested_stake) {
                  return (
                    <Chip
                      label={`Stake: ${recPick.suggested_stake.toFixed(2)}u`}
                      color="warning"
                      variant="filled"
                      size="small"
                      sx={{
                        fontWeight: 700,
                        color: "#1a1a1a",
                        bgcolor: "#f59e0b",
                      }} // Dark text on amber
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

{/* Picks Tabs Summary */}
          <Typography variant="caption" sx={{ display: "block", mb: 1, fontSize: { xs: "0.75rem", sm: "0.8rem" }, color: "text.secondary" }}>
            <strong>Picks Available:</strong> {prediction?.suggested_picks?.length || 0} picks
          </Typography>

          {/* Market Type Labels */}
          {prediction?.suggested_picks && prediction.suggested_picks.length > 0 && (
            <Box display="flex" flexWrap="wrap" gap={1} sx={{ mt: 0.5, mb: 1 }}>
              {prediction.suggested_picks.slice(0, 3).map((pick, idx) => (
                <Typography
                  key={`${pick.market_type}-${idx}`}
                  variant="caption"
                  sx={{ fontSize: { xs: "0.65rem", sm: "0.7rem" }, color: "text.secondary" }}
                >
                  {pick.market_type}
                </Typography>
              ))}
            </Box>
          )}

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

          <Divider sx={{ mb: 2 }} />
        </CardContent>
        </Card>
        {/* ScoreMatrixModal lives OUTSIDE the Card on purpose: MUI Dialog
            portals to document.body DOM-wise, but React synthetic events still
            bubble through the React component tree. Rendering it inside the
            Card made every click inside the dialog (close button, matrix,
            backdrop) bubble to the Card's onClick, reopening the details
            modal — the infinite open/close loop. As a Card sibling, dialog
            clicks no longer reach the Card handler. */}
        <ScoreMatrixModal
          open={matrixOpen}
          onClose={() => setMatrixOpen(false)}
          prediction={prediction}
        />
      </>
    );
  }
);

// Display name for debugging
MatchCard.displayName = "MatchCard";

export default MatchCard;

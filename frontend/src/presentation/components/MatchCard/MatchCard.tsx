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
  Divider,
  Checkbox,
  CircularProgress,
} from "@mui/material";
import { Chip } from "@mui/material";
import Schedule from "@mui/icons-material/Schedule";

import type { MatchPrediction } from "../../../types";
import { useCacheStore } from "../../../application/stores/useCacheStore";
import { ScoreMatrixModal } from "../MatchDetails/components/ScoreMatrixModal";

import { MatchBadges } from "./MatchBadges";
import { TeamDisplay } from "./TeamDisplay";
import { ScoreProbabilities } from "./ScoreProbabilities";
import { ProbabilityBars, OverUnderChips, ConfidenceSources } from "./MatchProbabilities";
import { RecommendationSection } from "./RecommendationSection";

interface MatchCardProps {
  matchPrediction: MatchPrediction;
  highlight?: boolean;
  onClick?: () => void;
  isSelected?: boolean;
  isLoading?: boolean;
  onToggleSelection?: () => void;
  match?: MatchPrediction["match"];
}

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

const getProbabilityColor = (value: number): string => {
  if (value >= 0.5) return "#10b981";
  if (value >= 0.35) return "#f59e0b";
  return "#ef4444";
};

const getCardSx = (highlight?: boolean, clickable?: boolean): Record<string, unknown> => ({
  height: "100%",
  position: "relative" as const,
  cursor: clickable ? "pointer" : "default",
  background: "linear-gradient(165deg, rgba(20, 25, 35, 0.85) 0%, rgba(10, 14, 23, 0.95) 100%)",
  backdropFilter: "blur(24px)",
  borderRadius: "24px",
  border: highlight
    ? "1px solid rgba(59, 130, 246, 0.5)"
    : "1px solid rgba(255, 255, 255, 0.08)",
  boxShadow: highlight
    ? "0 0 30px rgba(59, 130, 246, 0.25), inset 0 1px 0 rgba(255,255,255,0.1)"
    : "0 15px 35px -5px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255,255,255,0.1), inset 0 0 20px rgba(0,0,0,0.2)",
  transition: "all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1)",
  "&:hover": {
    transform: clickable ? "translateY(-6px) scale(1.01)" : "none",
    boxShadow: highlight
      ? "0 0 50px rgba(59, 130, 246, 0.4), inset 0 1px 0 rgba(255,255,255,0.2)"
      : "0 25px 50px -12px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255,255,255,0.2)",
    borderColor: highlight ? "#3b82f6" : "rgba(255, 255, 255, 0.2)",
  },
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
    const prefetchMatch = useCacheStore((state) => state.prefetchMatch);
    const prefetchTimerRef = React.useRef<NodeJS.Timeout | null>(null);

    const handleMouseEnter = (): void => {
      if (prefetchTimerRef.current) clearTimeout(prefetchTimerRef.current);
      prefetchTimerRef.current = setTimeout(() => {
        prefetchMatch(match.id);
      }, 300);
    };

    const handleMouseLeave = (): void => {
      if (prefetchTimerRef.current) {
        clearTimeout(prefetchTimerRef.current);
        prefetchTimerRef.current = null;
      }
    };

    React.useEffect(() => {
      return () => {
        if (prefetchTimerRef.current) clearTimeout(prefetchTimerRef.current);
      };
    }, []);

    const formattedDate = formatDate(match.match_date);
    // homeGoals/awayGoals moved to TeamDisplay component
    const homeWinPercent = formatPercent(prediction.home_win_probability);
    const drawPercent = formatPercent(prediction.draw_probability);
    const awayWinPercent = formatPercent(prediction.away_win_probability);
    const overPercent = formatPercent(prediction.over_25_probability);
    const underPercent = formatPercent(prediction.under_25_probability);
    const confidencePercent = formatPercent(prediction.confidence);
    const sourcesTooltip = `Fuentes: ${prediction.data_sources.join(", ")}`;
    const homeWinColor = getProbabilityColor(prediction.home_win_probability);
    const drawColor = getProbabilityColor(prediction.draw_probability);
    const awayWinColor = getProbabilityColor(prediction.away_win_probability);
    const isLive = ["1H", "2H", "HT", "LIVE", "ET", "P"].includes(match.status);
    const isFinished = ["FT", "AET", "PEN"].includes(match.status);
    const hasRichData = prediction.data_sources.some((s) => s.includes("FotMob"));

    return (
      <>
        <Card
          sx={getCardSx(highlight, !!onClick)}
          onClick={onClick}
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
        >
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

          <MatchBadges prediction={prediction} highlight={highlight} hasRichData={hasRichData} />

          <CardContent>
            <Box display="flex" alignItems="center" gap={1} mb={2} pl={onToggleSelection ? 3 : 0}>
              <Schedule fontSize="small" color="secondary" />
              <Typography variant="caption" color="text.secondary">{formattedDate}</Typography>
              {isLive && (
                <Chip
                  label="EN VIVO"
                  color="error"
                  size="small"
                  sx={{ height: 20, fontSize: "0.625rem", color: "#ffffff", fontWeight: 700 }}
                />
              )}
              {isFinished && (
                <Chip
                  label="FINALIZADO"
                  color="default"
                  sx={{ height: 20, fontSize: "0.625rem", color: "#ffffff", bgcolor: "rgba(255,255,255,0.2)" }}
                />
              )}
            </Box>

            <TeamDisplay match={match} prediction={prediction} />

            <ScoreProbabilities prediction={prediction} onOpenMatrix={() => setMatrixOpen(true)} />

            <Divider sx={{ mb: 2 }} />

            <ProbabilityBars
              prediction={prediction}
              homeWinPercent={homeWinPercent}
              drawPercent={drawPercent}
              awayWinPercent={awayWinPercent}
              homeWinColor={homeWinColor}
              drawColor={drawColor}
              awayWinColor={awayWinColor}
            />

            <Divider sx={{ mb: 2 }} />

            <OverUnderChips prediction={prediction} overPercent={overPercent} underPercent={underPercent} />

            <Divider sx={{ mb: 2 }} />

            <RecommendationSection prediction={prediction} />

            <ConfidenceSources
              confidencePercent={confidencePercent}
              sourcesTooltip={sourcesTooltip}
              dataSourcesLength={prediction.data_sources.length}
            />

            <Divider sx={{ mb: 2 }} />
          </CardContent>
        </Card>

        <ScoreMatrixModal
          open={matrixOpen}
          onClose={() => setMatrixOpen(false)}
          prediction={prediction}
        />
      </>
    );
  }
);

MatchCard.displayName = "MatchCard";

export default MatchCard;

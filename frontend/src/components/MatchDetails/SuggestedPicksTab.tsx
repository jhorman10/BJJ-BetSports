import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Alert,
  CircularProgress,
} from "@mui/material";
import {
  TipsAndUpdates,
  Warning,
  Star,
  StarHalf,
  StarOutline,
} from "@mui/icons-material";
import { SuggestedPick, MatchSuggestedPicks } from "../../types";
import api from "../../services/api";

interface SuggestedPicksTabProps {
  matchId: string;
}

/**
 * Get color scheme based on probability
 */
const getColorScheme = (
  probability: number
): {
  border: string;
  glow: string;
  badge: string;
  starColor: string;
} => {
  if (probability > 0.8) {
    return {
      border: "#22c55e",
      glow: "0 0 24px rgba(34, 197, 94, 0.4), 0 0 48px rgba(34, 197, 94, 0.2)",
      badge: "#22c55e",
      starColor: "#22c55e",
    };
  } else if (probability > 0.6) {
    return {
      border: "#f59e0b",
      glow: "0 0 24px rgba(245, 158, 11, 0.4), 0 0 48px rgba(245, 158, 11, 0.2)",
      badge: "#f59e0b",
      starColor: "#f59e0b",
    };
  }
  return {
    border: "#ef4444",
    glow: "0 0 24px rgba(239, 68, 68, 0.4), 0 0 48px rgba(239, 68, 68, 0.2)",
    badge: "#ef4444",
    starColor: "#ef4444",
  };
};

/**
 * Star rating component
 */
const StarRating: React.FC<{ probability: number; color: string }> = ({
  probability,
  color,
}) => {
  const stars = probability * 5;
  const fullStars = Math.floor(stars);
  const hasHalfStar = stars - fullStars >= 0.5;
  const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

  return (
    <Box display="flex" alignItems="center" gap={0.25}>
      {[...Array(fullStars)].map((_, i) => (
        <Star key={`full-${i}`} sx={{ fontSize: 18, color }} />
      ))}
      {hasHalfStar && <StarHalf sx={{ fontSize: 18, color }} />}
      {[...Array(emptyStars)].map((_, i) => (
        <StarOutline
          key={`empty-${i}`}
          sx={{ fontSize: 18, color: "rgba(255,255,255,0.2)" }}
        />
      ))}
    </Box>
  );
};

/**
 * Risk dots indicator
 */
const RiskDots: React.FC<{ level: number; color: string }> = ({
  level,
  color,
}) => {
  return (
    <Box display="flex" alignItems="center" gap={0.75}>
      <Typography
        variant="caption"
        sx={{
          color: "rgba(255,255,255,0.5)",
          fontSize: "0.7rem",
          fontWeight: 500,
          letterSpacing: "0.5px",
        }}
      >
        Risk:
      </Typography>
      {[1, 2, 3, 4, 5].map((dot) => (
        <Box
          key={dot}
          sx={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            bgcolor: dot <= level ? color : "rgba(255,255,255,0.15)",
            transition: "all 0.3s ease",
          }}
        />
      ))}
    </Box>
  );
};

/**
 * Get market icon
 */
const getMarketIcon = (marketType: string): string => {
  switch (marketType) {
    case "corners_over":
    case "corners_under":
      return "⚑";
    case "cards_over":
    case "cards_under":
      return "🟨";
    case "va_handicap":
      return "⚖️";
    case "goals_over":
      return "⚽";
    case "goals_under":
      return "🛡️";
    default:
      return "📊";
  }
};

/**
 * Pick Card Component - Matching reference design exactly
 */
const PickCard: React.FC<{ pick: SuggestedPick }> = ({ pick }) => {
  const colors = getColorScheme(pick.probability);
  const confidenceText =
    pick.probability > 0.8 ? "5" : pick.probability > 0.6 ? "4" : "3";

  return (
    <Card
      sx={{
        mb: 2,
        background:
          "linear-gradient(145deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)",
        borderLeft: `4px solid ${colors.border}`,
        borderRadius: "16px",
        boxShadow: colors.glow,
        overflow: "visible",
        transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        "&:hover": {
          transform: "translateY(-3px) scale(1.01)",
          boxShadow: `${colors.glow}, 0 16px 40px rgba(0,0,0,0.4)`,
        },
      }}
    >
      <CardContent sx={{ p: 2.5, "&:last-child": { pb: 2.5 } }}>
        {/* Header Row: Icon + Title + Badge */}
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="flex-start"
          mb={1.5}
        >
          <Box display="flex" alignItems="center" gap={1.5} flex={1}>
            <Typography
              sx={{
                fontSize: "1.4rem",
                lineHeight: 1,
              }}
            >
              {getMarketIcon(pick.market_type)}
            </Typography>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 700,
                fontSize: "1.1rem",
                color: "#ffffff",
                letterSpacing: "-0.02em",
                fontFamily:
                  "'Inter', 'SF Pro Display', -apple-system, sans-serif",
              }}
            >
              {pick.market_label}
            </Typography>
          </Box>
          <Chip
            label={`${(pick.probability * 100).toFixed(0)}% Prob.`}
            size="medium"
            sx={{
              bgcolor: colors.badge,
              color: "white",
              fontWeight: 700,
              fontSize: "0.85rem",
              height: 32,
              px: 0.5,
              borderRadius: "8px",
              fontFamily: "'Inter', 'SF Pro Display', sans-serif",
              boxShadow: `0 4px 12px ${colors.badge}40`,
            }}
          />
        </Box>

        {/* Star Rating Row */}
        <Box display="flex" alignItems="center" gap={1.5} mb={2}>
          <StarRating probability={pick.probability} color={colors.starColor} />
          <Typography
            variant="caption"
            sx={{
              color: "rgba(255,255,255,0.5)",
              fontSize: "0.75rem",
              fontFamily: "'Inter', sans-serif",
            }}
          >
            {confidenceText}-star confidence
          </Typography>
        </Box>

        {/* Description */}
        <Typography
          variant="body2"
          sx={{
            color: "rgba(255,255,255,0.7)",
            fontSize: "0.875rem",
            lineHeight: 1.6,
            mb: 2,
            fontFamily: "'Inter', sans-serif",
          }}
        >
          {pick.reasoning}
        </Typography>

        {/* Risk Indicator - Bottom Right */}
        <Box display="flex" justifyContent="flex-end">
          <RiskDots level={pick.risk_level} color={colors.border} />
        </Box>
      </CardContent>
    </Card>
  );
};

/**
 * Suggested Picks Tab Component
 */
const SuggestedPicksTab: React.FC<SuggestedPicksTabProps> = ({ matchId }) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [picks, setPicks] = useState<MatchSuggestedPicks | null>(null);

  useEffect(() => {
    const fetchPicks = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getSuggestedPicks(matchId);
        setPicks(data);
      } catch (err) {
        console.error("Error fetching suggested picks:", err);
        setError("No se pudieron cargar los picks sugeridos");
      } finally {
        setLoading(false);
      }
    };

    if (matchId) {
      fetchPicks();
    }
  }, [matchId]);

  if (loading) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        py={4}
      >
        <CircularProgress size={40} sx={{ color: "#22c55e" }} />
        <Typography
          variant="body2"
          sx={{
            color: "rgba(255,255,255,0.6)",
            mt: 2,
            fontFamily: "'Inter', sans-serif",
          }}
        >
          Analizando estadísticas...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2, borderRadius: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!picks || picks.suggested_picks.length === 0) {
    return (
      <Box textAlign="center" py={4}>
        <TipsAndUpdates
          sx={{ fontSize: 48, color: "rgba(255,255,255,0.3)", mb: 2 }}
        />
        <Typography sx={{ color: "rgba(255,255,255,0.6)" }}>
          No hay picks sugeridos disponibles para este partido.
        </Typography>
      </Box>
    );
  }

  // Sort picks by probability (highest first)
  const sortedPicks = [...picks.suggested_picks].sort(
    (a, b) => b.probability - a.probability
  );

  return (
    <Box sx={{ mt: 1 }}>
      {/* Combination Warning */}
      {picks.combination_warning &&
        !picks.combination_warning.includes("Datos históricos limitados") && (
          <Alert
            severity="warning"
            icon={<Warning />}
            sx={{
              mb: 3,
              bgcolor: "rgba(245, 158, 11, 0.1)",
              border: "1px solid rgba(245, 158, 11, 0.3)",
              borderRadius: "12px",
              "& .MuiAlert-message": {
                fontFamily: "'Inter', sans-serif",
              },
            }}
          >
            <Typography variant="body2">{picks.combination_warning}</Typography>
          </Alert>
        )}

      {/* Pick Cards */}
      {sortedPicks.map((pick, index) => (
        <PickCard key={`pick-${index}`} pick={pick} />
      ))}
    </Box>
  );
};

export default SuggestedPicksTab;

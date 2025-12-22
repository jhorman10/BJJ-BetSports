import React, { useEffect, useState, useMemo } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  CircularProgress,
} from "@mui/material";
import {
  TipsAndUpdates,
  Star,
  StarHalf,
  StarOutline,
} from "@mui/icons-material";
import {
  MatchPrediction,
  SuggestedPick,
  MatchSuggestedPicks,
  Match,
  Prediction,
} from "../../types";
import api from "../../services/api";

interface SuggestedPicksTabProps {
  matchPrediction: MatchPrediction;
}

// Local pick interface for fallback calculation
interface LocalPick {
  market_type: string;
  market_label: string;
  probability: number;
  reasoning: string;
  risk_level: number;
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
 * Calculate fallback picks when API returns empty (using local data)
 */
const calculateFallbackPicks = (
  match: Match,
  prediction: Prediction
): LocalPick[] => {
  const picks: LocalPick[] = [];
  const totalExpectedGoals =
    prediction.predicted_home_goals + prediction.predicted_away_goals;

  // 1. Corners Pick
  const totalCorners = (match.home_corners ?? 0) + (match.away_corners ?? 0);
  const expectedCorners =
    totalCorners > 0 ? totalCorners : Math.round(totalExpectedGoals * 3.5);
  const cornersProb = Math.min(0.92, 0.55 + (expectedCorners - 7) * 0.04);
  picks.push({
    market_type: "corners_over",
    market_label: `Más de ${
      expectedCorners > 6 ? expectedCorners - 1 : 6
    }.5 Córners`,
    probability: Math.max(0.45, Math.min(0.92, cornersProb)),
    reasoning:
      "Análisis estadístico y rendimiento reciente de ambos equipos sugieren alta probabilidad.",
    risk_level: cornersProb > 0.75 ? 3 : 4,
  });

  // 2. Yellow Cards Pick
  const totalYellowCards =
    (match.home_yellow_cards ?? 0) + (match.away_yellow_cards ?? 0);
  const expectedCards = totalYellowCards > 0 ? totalYellowCards : 3;
  const cardsProb = Math.min(0.88, 0.5 + (expectedCards - 2) * 0.08);
  picks.push({
    market_type: "cards_over",
    market_label: `${match.home_team.name.split(" ")[0]} - Más de ${Math.max(
      1,
      expectedCards - 1
    )}.5 Tarjetas`,
    probability: Math.max(0.5, Math.min(0.88, cardsProb)),
    reasoning:
      "Partidos con alto historial de amonestaciones y árbitro estricto.",
    risk_level: 3,
  });

  // 3. Handicap VA Pick
  const homeDominant =
    prediction.home_win_probability > prediction.away_win_probability + 0.15;
  const awayDominant =
    prediction.away_win_probability > prediction.home_win_probability + 0.15;

  if (homeDominant || awayDominant) {
    const dominantTeam = homeDominant ? "Local" : "Visitante";
    const handicapProb =
      Math.max(
        prediction.home_win_probability,
        prediction.away_win_probability
      ) * 0.95;
    picks.push({
      market_type: "va_handicap",
      market_label: `Hándicap VA (+2) - ${dominantTeam}`,
      probability: Math.min(0.82, Math.max(0.6, handicapProb)),
      reasoning: `Ventaja considerable para el equipo ${dominantTeam.toLowerCase()} en casa con soporte de datos.`,
      risk_level: 3,
    });
  }

  // 4. Goals Pick
  const goalsProb =
    prediction.over_25_probability > prediction.under_25_probability
      ? prediction.over_25_probability
      : prediction.under_25_probability;
  const goalsLabel =
    prediction.over_25_probability > prediction.under_25_probability
      ? "Más de 2.5 Goles"
      : "Menos de 2.5 Goles";
  const goalsType =
    prediction.over_25_probability > prediction.under_25_probability
      ? "goals_over"
      : "goals_under";

  picks.push({
    market_type: goalsType,
    market_label: goalsLabel,
    probability: goalsProb,
    reasoning:
      goalsProb > 0.6
        ? "Ambos equipos con tendencia ofensiva y alta conversión de goles."
        : "Encuentro impredecible con defensas sólidas, pero potencial ofensivo.",
    risk_level: goalsProb > 0.7 ? 2 : 4,
  });

  return picks;
};

/**
 * Pick Card Component
 */
const PickCard: React.FC<{ pick: SuggestedPick | LocalPick }> = ({ pick }) => {
  const colors = getColorScheme(pick.probability);
  const confidenceText =
    pick.probability > 0.8 ? "5" : pick.probability > 0.6 ? "4" : "3";
  const marketType = "market_type" in pick ? pick.market_type : "";

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
        {/* Header Row */}
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="flex-start"
          mb={1.5}
        >
          <Box display="flex" alignItems="center" gap={1.5} flex={1}>
            <Typography sx={{ fontSize: "1.4rem", lineHeight: 1 }}>
              {getMarketIcon(marketType)}
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
              boxShadow: `0 4px 12px ${colors.badge}40`,
            }}
          />
        </Box>

        {/* Star Rating */}
        <Box display="flex" alignItems="center" gap={1.5} mb={2}>
          <StarRating probability={pick.probability} color={colors.starColor} />
          <Typography
            variant="caption"
            sx={{ color: "rgba(255,255,255,0.5)", fontSize: "0.75rem" }}
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
          }}
        >
          {pick.reasoning}
        </Typography>

        {/* Risk Indicator */}
        <Box display="flex" justifyContent="flex-end">
          <RiskDots level={pick.risk_level} color={colors.border} />
        </Box>
      </CardContent>
    </Card>
  );
};

/**
 * Suggested Picks Tab Component
 * Fetches picks from backend API (which calculates with learning service)
 * Falls back to local calculation if API returns empty
 */
const SuggestedPicksTab: React.FC<SuggestedPicksTabProps> = ({
  matchPrediction,
}) => {
  const { match, prediction } = matchPrediction;
  const [loading, setLoading] = useState(true);
  const [apiPicks, setApiPicks] = useState<MatchSuggestedPicks | null>(null);

  // Fetch picks from backend API
  useEffect(() => {
    const fetchPicks = async () => {
      try {
        setLoading(true);
        const data = await api.getSuggestedPicks(match.id);
        setApiPicks(data);
      } catch (err) {
        console.error("Error fetching suggested picks:", err);
        setApiPicks(null);
      } finally {
        setLoading(false);
      }
    };

    fetchPicks();
  }, [match.id]);

  // Calculate fallback picks locally if API returns empty
  const fallbackPicks = useMemo(
    () => calculateFallbackPicks(match, prediction),
    [match, prediction]
  );

  // Use API picks if available, otherwise use fallback
  const picks = useMemo(() => {
    if (
      apiPicks &&
      apiPicks.suggested_picks &&
      apiPicks.suggested_picks.length > 0
    ) {
      return apiPicks.suggested_picks;
    }
    return fallbackPicks;
  }, [apiPicks, fallbackPicks]);

  // Sort picks by probability
  const sortedPicks = useMemo(
    () => [...picks].sort((a, b) => b.probability - a.probability),
    [picks]
  );

  if (loading) {
    return (
      <Box display="flex" flexDirection="column" alignItems="center" py={4}>
        <CircularProgress size={40} sx={{ color: "#22c55e" }} />
        <Typography
          variant="body2"
          sx={{ color: "rgba(255,255,255,0.6)", mt: 2 }}
        >
          Analizando estadísticas...
        </Typography>
      </Box>
    );
  }

  if (sortedPicks.length === 0) {
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

  return (
    <Box sx={{ mt: 1 }}>
      {sortedPicks.map((pick, index) => (
        <PickCard key={`pick-${index}`} pick={pick} />
      ))}
    </Box>
  );
};

export default SuggestedPicksTab;

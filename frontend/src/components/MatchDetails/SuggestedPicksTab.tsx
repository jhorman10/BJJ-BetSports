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
 * Get border and glow color based on probability
 */
const getColorScheme = (
  probability: number
): { border: string; glow: string; badge: string } => {
  if (probability > 0.8) {
    return {
      border: "#4caf50",
      glow: "0 0 20px rgba(76, 175, 80, 0.3)",
      badge: "#4caf50",
    };
  } else if (probability > 0.6) {
    return {
      border: "#ff9800",
      glow: "0 0 20px rgba(255, 152, 0, 0.3)",
      badge: "#ff9800",
    };
  }
  return {
    border: "#f44336",
    glow: "0 0 20px rgba(244, 67, 54, 0.3)",
    badge: "#f44336",
  };
};

/**
 * Star rating component based on probability
 */
const StarRating: React.FC<{ probability: number }> = ({ probability }) => {
  // Convert probability to 5-star scale
  const stars = probability * 5;
  const fullStars = Math.floor(stars);
  const hasHalfStar = stars - fullStars >= 0.5;
  const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

  const starColor =
    probability > 0.8 ? "#4caf50" : probability > 0.6 ? "#ff9800" : "#f44336";

  return (
    <Box display="flex" alignItems="center" gap={0.25}>
      {[...Array(fullStars)].map((_, i) => (
        <Star key={`full-${i}`} sx={{ fontSize: 16, color: starColor }} />
      ))}
      {hasHalfStar && <StarHalf sx={{ fontSize: 16, color: starColor }} />}
      {[...Array(emptyStars)].map((_, i) => (
        <StarOutline
          key={`empty-${i}`}
          sx={{ fontSize: 16, color: "grey.600" }}
        />
      ))}
    </Box>
  );
};

/**
 * Risk level indicator with dots
 */
const RiskDots: React.FC<{ level: number }> = ({ level }) => {
  const getColor = (dotIndex: number) => {
    if (dotIndex > level) return "grey.700";
    if (level <= 2) return "#4caf50";
    if (level <= 3) return "#ff9800";
    return "#f44336";
  };

  return (
    <Box display="flex" alignItems="center" gap={0.5}>
      <Typography variant="caption" color="text.secondary" sx={{ mr: 0.5 }}>
        Risk:
      </Typography>
      {[1, 2, 3, 4, 5].map((dot) => (
        <Box
          key={dot}
          sx={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            bgcolor: getColor(dot),
            transition: "background-color 0.3s",
          }}
        />
      ))}
    </Box>
  );
};

/**
 * Single pick card matching the mockup design
 */
const PickCard: React.FC<{ pick: SuggestedPick }> = ({ pick }) => {
  const colors = getColorScheme(pick.probability);

  return (
    <Card
      sx={{
        mb: 2,
        background:
          "linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%)",
        borderLeft: `4px solid ${colors.border}`,
        borderRadius: 2,
        boxShadow: colors.glow,
        transition: "transform 0.2s, box-shadow 0.2s",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: `${colors.glow}, 0 8px 25px rgba(0,0,0,0.3)`,
        },
      }}
    >
      <CardContent sx={{ p: 2.5, "&:last-child": { pb: 2.5 } }}>
        {/* Header with title and probability badge */}
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="flex-start"
          mb={1}
        >
          <Box flex={1}>
            <Typography
              variant="h6"
              fontWeight="bold"
              sx={{
                fontSize: "1.1rem",
                color: "white",
                display: "flex",
                alignItems: "center",
                gap: 1,
              }}
            >
              {pick.market_type === "corners_over" && "⚑ "}
              {pick.market_type === "cards_over" && "🟨 "}
              {pick.market_type === "va_handicap" && "⚖️ "}
              {pick.market_type === "goals_over" && "⚽ "}
              {pick.market_type === "goals_under" && "🛡️ "}
              {pick.market_label}
            </Typography>
          </Box>
          <Chip
            label={`${(pick.probability * 100).toFixed(0)}% Prob.`}
            size="medium"
            sx={{
              bgcolor: colors.badge,
              color: "white",
              fontWeight: "bold",
              fontSize: "0.9rem",
              height: 32,
              ml: 2,
            }}
          />
        </Box>

        {/* Star rating */}
        <Box display="flex" alignItems="center" gap={1} mb={1.5}>
          <StarRating probability={pick.probability} />
          <Typography variant="caption" color="text.secondary">
            {pick.probability > 0.8 ? "5" : pick.probability > 0.6 ? "4" : "3"}
            -star confidence
          </Typography>
        </Box>

        {/* Reasoning text */}
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            mb: 2,
            lineHeight: 1.5,
          }}
        >
          {pick.reasoning}
        </Typography>

        {/* Risk indicator */}
        <Box display="flex" justifyContent="flex-end">
          <RiskDots level={pick.risk_level} />
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
        <CircularProgress size={40} sx={{ color: "#4caf50" }} />
        <Typography variant="body2" color="text.secondary" mt={2}>
          Analizando estadísticas...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!picks || picks.suggested_picks.length === 0) {
    return (
      <Box textAlign="center" py={4}>
        <TipsAndUpdates sx={{ fontSize: 48, color: "text.secondary", mb: 2 }} />
        <Typography color="text.secondary">
          No hay picks sugeridos disponibles para este partido.
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Esto puede deberse a falta de datos históricos suficientes.
        </Typography>
      </Box>
    );
  }

  // Sort picks by probability (highest first)
  const sortedPicks = [...picks.suggested_picks].sort(
    (a, b) => b.probability - a.probability
  );

  return (
    <Box sx={{ mt: 2 }}>
      {/* Combination Warning */}
      {picks.combination_warning && (
        <Alert
          severity="warning"
          icon={<Warning />}
          sx={{
            mb: 3,
            bgcolor: "rgba(255, 152, 0, 0.1)",
            border: "1px solid rgba(255, 152, 0, 0.3)",
            borderRadius: 2,
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

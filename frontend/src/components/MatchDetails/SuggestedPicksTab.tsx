import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Alert,
  CircularProgress,
  Tooltip,
  Divider,
} from "@mui/material";
import {
  TipsAndUpdates,
  Warning,
  CheckCircle,
  RadioButtonUnchecked,
} from "@mui/icons-material";
import { SuggestedPick, MatchSuggestedPicks } from "../../types";
import api from "../../services/api";

interface SuggestedPicksTabProps {
  matchId: string;
}

/**
 * Get color based on probability and confidence level
 */
const getConfidenceColor = (
  probability: number,
  confidenceLevel: string
): "success" | "warning" | "error" => {
  if (probability > 0.8 || confidenceLevel === "high") {
    return "success";
  } else if (probability > 0.6 || confidenceLevel === "medium") {
    return "warning";
  }
  return "error";
};

/**
 * Get border color for card based on probability
 */
const getBorderColor = (probability: number): string => {
  if (probability > 0.8) {
    return "#4caf50"; // Green
  } else if (probability > 0.6) {
    return "#ff9800"; // Orange
  }
  return "#f44336"; // Red
};

/**
 * Risk level indicator component
 */
const RiskIndicator: React.FC<{ level: number }> = ({ level }) => {
  const dots = [];
  for (let i = 1; i <= 5; i++) {
    dots.push(
      <Box
        key={i}
        component="span"
        sx={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          display: "inline-block",
          mx: 0.25,
          bgcolor:
            i <= level
              ? level <= 2
                ? "success.main"
                : level <= 3
                ? "warning.main"
                : "error.main"
              : "grey.600",
        }}
      />
    );
  }
  return (
    <Tooltip title={`Nivel de riesgo: ${level}/5`}>
      <Box sx={{ display: "flex", alignItems: "center" }}>{dots}</Box>
    </Tooltip>
  );
};

/**
 * Single pick card component
 */
const PickCard: React.FC<{ pick: SuggestedPick }> = ({ pick }) => {
  const borderColor = getBorderColor(pick.probability);
  const chipColor = getConfidenceColor(pick.probability, pick.confidence_level);

  return (
    <Card
      sx={{
        mb: 2,
        borderLeft: `4px solid ${borderColor}`,
        bgcolor: "rgba(30, 41, 59, 0.6)",
        backdropFilter: "blur(10px)",
        transition: "transform 0.2s, box-shadow 0.2s",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: `0 4px 20px ${borderColor}40`,
        },
      }}
    >
      <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="flex-start"
        >
          <Box flex={1}>
            <Box display="flex" alignItems="center" gap={1} mb={0.5}>
              {pick.is_recommended ? (
                <CheckCircle sx={{ fontSize: 16, color: "success.main" }} />
              ) : (
                <RadioButtonUnchecked
                  sx={{ fontSize: 16, color: "grey.500" }}
                />
              )}
              <Typography variant="subtitle1" fontWeight="bold">
                {pick.market_label}
              </Typography>
            </Box>
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ mb: 1.5, pl: 3 }}
            >
              {pick.reasoning}
            </Typography>
          </Box>
          <Box textAlign="right" ml={2}>
            <Chip
              label={`${(pick.probability * 100).toFixed(0)}%`}
              color={chipColor}
              size="medium"
              sx={{
                fontWeight: "bold",
                fontSize: "1rem",
                minWidth: 60,
              }}
            />
          </Box>
        </Box>
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          mt={1}
          pt={1}
          borderTop="1px solid rgba(255,255,255,0.1)"
        >
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="caption" color="text.secondary">
              Riesgo:
            </Typography>
            <RiskIndicator level={pick.risk_level} />
          </Box>
          <Chip
            label={
              pick.confidence_level === "high"
                ? "Alta confianza"
                : pick.confidence_level === "medium"
                ? "Confianza media"
                : "Baja confianza"
            }
            size="small"
            variant="outlined"
            sx={{
              borderColor: borderColor,
              color: borderColor,
              fontSize: "0.7rem",
            }}
          />
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
        <CircularProgress size={40} />
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

  // Separate recommended and not recommended picks
  const recommendedPicks = picks.suggested_picks.filter(
    (p) => p.is_recommended
  );
  const otherPicks = picks.suggested_picks.filter((p) => !p.is_recommended);

  return (
    <Box sx={{ mt: 2 }}>
      {/* Combination Warning */}
      {picks.combination_warning && (
        <Alert
          severity="warning"
          icon={<Warning />}
          sx={{
            mb: 2,
            bgcolor: "rgba(255, 152, 0, 0.1)",
            border: "1px solid rgba(255, 152, 0, 0.3)",
          }}
        >
          <Typography variant="body2">{picks.combination_warning}</Typography>
        </Alert>
      )}

      {/* Legend */}
      <Box
        display="flex"
        gap={2}
        mb={2}
        flexWrap="wrap"
        justifyContent="center"
      >
        <Box display="flex" alignItems="center" gap={0.5}>
          <Box
            sx={{
              width: 12,
              height: 12,
              bgcolor: "#4caf50",
              borderRadius: 0.5,
            }}
          />
          <Typography variant="caption" color="text.secondary">
            &gt;80% - Alta probabilidad
          </Typography>
        </Box>
        <Box display="flex" alignItems="center" gap={0.5}>
          <Box
            sx={{
              width: 12,
              height: 12,
              bgcolor: "#ff9800",
              borderRadius: 0.5,
            }}
          />
          <Typography variant="caption" color="text.secondary">
            60-80% - Probabilidad media
          </Typography>
        </Box>
        <Box display="flex" alignItems="center" gap={0.5}>
          <Box
            sx={{
              width: 12,
              height: 12,
              bgcolor: "#f44336",
              borderRadius: 0.5,
            }}
          />
          <Typography variant="caption" color="text.secondary">
            &lt;60% - Baja probabilidad
          </Typography>
        </Box>
      </Box>

      <Divider sx={{ mb: 2 }} />

      {/* Recommended Picks Section */}
      {recommendedPicks.length > 0 && (
        <Box mb={3}>
          <Typography
            variant="subtitle2"
            color="success.main"
            gutterBottom
            sx={{ display: "flex", alignItems: "center", gap: 1 }}
          >
            <CheckCircle sx={{ fontSize: 18 }} />
            Picks Recomendados ({recommendedPicks.length})
          </Typography>
          {recommendedPicks.map((pick, index) => (
            <PickCard key={`rec-${index}`} pick={pick} />
          ))}
        </Box>
      )}

      {/* Other Picks Section */}
      {otherPicks.length > 0 && (
        <Box>
          <Typography
            variant="subtitle2"
            color="text.secondary"
            gutterBottom
            sx={{ display: "flex", alignItems: "center", gap: 1 }}
          >
            <RadioButtonUnchecked sx={{ fontSize: 18 }} />
            Otros Mercados ({otherPicks.length})
          </Typography>
          {otherPicks.map((pick, index) => (
            <PickCard key={`other-${index}`} pick={pick} />
          ))}
        </Box>
      )}

      {/* Disclaimer */}
      <Box mt={3} pt={2} borderTop="1px solid rgba(255,255,255,0.1)">
        <Typography
          variant="caption"
          color="text.secondary"
          textAlign="center"
          display="block"
        >
          ⚠️ Los picks sugeridos son solo orientativos. Basados en análisis
          estadístico de datos históricos. No garantizan resultados.
        </Typography>
      </Box>
    </Box>
  );
};

export default SuggestedPicksTab;

import React, { useEffect, useState, useMemo, memo } from "react";
import { Box, Typography, Chip, CircularProgress } from "@mui/material";
import { TipsAndUpdates } from "@mui/icons-material";
import {
  MatchPrediction,
  SuggestedPick,
  MatchSuggestedPicks,
} from "../../../types";
import api from "../../../services/api";
import { generateFallbackPicks } from "../../../utils/predictionUtils";
import {
  getPickColor,
  getMarketIcon,
  getUniquePicks,
} from "../../../utils/marketUtils";

interface SuggestedPicksTabProps {
  matchPrediction: MatchPrediction;
  onPicksCount?: (count: number) => void;
}

// Utility functions imported from ../../../utils/marketUtils

/**
 * Single row pick item - compact design
 */
const PickRow: React.FC<{ pick: SuggestedPick }> = memo(({ pick }) => {
  const color = getPickColor(pick.probability);

  return (
    <>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          py: 1,
          px: 1.5,
          borderLeft: `3px solid ${color}`,
          bgcolor: `${color}15`,
          borderRadius: "8px",
          mb: 1,
          transition: "all 0.2s ease",
          "&:hover": {
            bgcolor: `${color}25`,
            transform: "translateX(2px)",
          },
        }}
      >
        <Box display="flex" alignItems="center" gap={1} flex={1}>
          <Typography sx={{ fontSize: "1rem" }}>
            {getMarketIcon(pick.market_type)}
          </Typography>
          <Typography
            variant="body2"
            sx={{
              fontWeight: 600,
              color: "#ffffff",
              fontSize: "0.85rem",
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
            }}
          >
            {pick.market_label}
          </Typography>
        </Box>
        <Chip
          label={`${(pick.probability * 100).toFixed(0)}%`}
          size="small"
          sx={{
            bgcolor: color,
            color: "white",
            fontWeight: 700,
            fontSize: "0.75rem",
            height: 24,
            minWidth: 45,
            "& .MuiChip-label": { px: 1 },
          }}
        />
      </Box>
      {pick.reasoning && (
        <Typography
          variant="caption"
          sx={{
            display: "block",
            fontSize: "0.75rem",
            color: "rgba(255,255,255,0.6)",
            mt: -0.5,
            mb: 1.5,
            pl: 1,
            fontStyle: "italic",
          }}
        >
          {pick.reasoning}
        </Typography>
      )}
    </>
  );
});

/**
 * Suggested Picks Tab Component
 * All data comes from the backend API - compact single-row design
 */
const SuggestedPicksTab: React.FC<SuggestedPicksTabProps> = ({
  matchPrediction,
  onPicksCount,
}) => {
  const { match } = matchPrediction;
  const [loading, setLoading] = useState(true);
  const [apiPicks, setApiPicks] = useState<MatchSuggestedPicks | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch picks from backend API
  useEffect(() => {
    const fetchPicks = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await api.getSuggestedPicks(match.id);
        setApiPicks(data);
      } catch (err: any) {
        if (err.response && err.response.status === 404) {
          setError("Datos insuficientes para generar picks");
        } else {
          console.error("Error fetching suggested picks:", err);
          setError("No se pudieron cargar los picks");
        }
        setApiPicks(null);
      } finally {
        setLoading(false);
      }
    };

    fetchPicks();
  }, [match.id]);

  // Sort picks by probability (highest first)
  const sortedPicks = useMemo(() => {
    let picks = apiPicks?.suggested_picks ? [...apiPicks.suggested_picks] : [];

    // Fallback Frontend: Si el backend no devolvió picks pero tenemos predicción,
    // generamos un pick basado en la data visible (probabilidades).
    if (apiPicks && picks.length === 0 && matchPrediction.prediction) {
      picks = generateFallbackPicks(matchPrediction);
    }

    // Filter duplicates to ensure unique picks
    picks = getUniquePicks(picks);

    // Sort by probability only (highest first)
    return picks.sort((a, b) => b.probability - a.probability);
  }, [apiPicks, matchPrediction]);

  // Report count to parent if callback exists
  useEffect(() => {
    if (onPicksCount) {
      onPicksCount(sortedPicks.length);
    }
  }, [sortedPicks.length, onPicksCount]);

  if (loading) {
    return (
      <Box display="flex" alignItems="center" justifyContent="center" py={3}>
        <CircularProgress size={24} sx={{ color: "#22c55e", mr: 1 }} />
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.6)" }}>
          Cargando picks...
        </Typography>
      </Box>
    );
  }

  if (error || sortedPicks.length === 0) {
    return (
      <Box display="flex" alignItems="center" justifyContent="center" py={2}>
        <TipsAndUpdates
          sx={{ fontSize: 24, color: "rgba(255,255,255,0.3)", mr: 1 }}
        />
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.5)" }}>
          {error || "Sin picks disponibles"}
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ maxHeight: "350px", overflowY: "auto", pr: 0.5 }}>
      {sortedPicks.map((pick, index) => (
        <PickRow key={`pick-${index}`} pick={pick} />
      ))}
    </Box>
  );
};

export default SuggestedPicksTab;

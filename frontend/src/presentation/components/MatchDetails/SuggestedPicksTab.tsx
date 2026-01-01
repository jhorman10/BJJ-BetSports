import React, { useEffect, useState, useMemo, memo } from "react";
import {
  Box,
  Typography,
  Chip,
  CircularProgress,
  Tabs,
  Tab,
} from "@mui/material";
import { TipsAndUpdates } from "@mui/icons-material";
import { MatchPrediction, SuggestedPick } from "../../../types";
import { generateFallbackPicks } from "../../../utils/predictionUtils";
import {
  getPickColor,
  getMarketIcon,
  getUniquePicks,
} from "../../../utils/marketUtils";
import { useCacheStore } from "../../../application/stores/useCacheStore";

interface SuggestedPicksTabProps {
  matchPrediction: MatchPrediction;
  onPicksCount?: (count: number) => void;
}

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
              wordBreak: "break-word",
              overflowWrap: "break-word",
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

// Helper to determine tab category
const getPickCategory = (marketType: string): string => {
  const type = marketType.toUpperCase();
  if (type.includes("CORNER")) return "CORNERS";
  if (type.includes("CARD")) return "CARDS";
  if (type.includes("HANDICAP") || type.includes("VA_HANDICAP"))
    return "HANDICAPS";
  if (type.includes("BTTS")) return "BTTS";
  if (
    type.includes("GOAL") ||
    type.includes("OVER") ||
    type.includes("UNDER")
  ) {
    return "GOALS";
  }
  if (
    type.includes("WIN") ||
    type.includes("DRAW") ||
    type.includes("CHANCE")
  ) {
    return "WINNER";
  }
  return "OTHER";
};

/**
 * Suggested Picks Tab Component
 * Separated by tabs: Top ML, Winner, Goals, Corners, Cards, Others
 */
const SuggestedPicksTab: React.FC<SuggestedPicksTabProps> = ({
  matchPrediction,
  onPicksCount,
}) => {
  const { match } = matchPrediction;

  // Use Cache Store
  const { getPicks, prefetchMatch, isFetching } = useCacheStore();

  // Get picks directly from synchronous local cache
  const cachedPicks = getPicks(match.id);
  const isLoading = isFetching(match.id);
  const hasPicks = cachedPicks && cachedPicks.length > 0;

  // Manual fallback fetching if needed (JIT)
  // This handles the edge case where prefetch hasn't happened yet
  useEffect(() => {
    if (!hasPicks && !isLoading) {
      prefetchMatch(match.id);
    }
  }, [match.id, hasPicks, isLoading, prefetchMatch]);

  const [currentTab, setCurrentTab] = useState("ALL");
  const [initialized, setInitialized] = useState(false);

  const loading = isLoading && !hasPicks;
  const error = !hasPicks && !isLoading ? "No suggested picks available" : null;
  const apiPicks = cachedPicks ? { suggested_picks: cachedPicks } : null;

  // Sort picks by probability (highest first)
  const sortedPicks = useMemo(() => {
    let picks = apiPicks?.suggested_picks ? [...apiPicks.suggested_picks] : [];

    // If API failed or returned explicit empty list, and we have prediction data, GENERATE FALLBACKS
    if ((!picks || picks.length === 0) && matchPrediction.prediction) {
      console.log("Generating fallback picks for", match.id);
      picks = generateFallbackPicks(matchPrediction);
    }

    picks = getUniquePicks(picks);
    return picks.sort((a, b) => b.probability - a.probability);
  }, [apiPicks, matchPrediction]);

  // Report count
  useEffect(() => {
    if (onPicksCount) {
      onPicksCount(sortedPicks.length);
    }
  }, [sortedPicks.length, onPicksCount]);

  // Calculate counts for each category to conditionally hide tabs
  const categoryCounts = useMemo(() => {
    const counts = {
      TOP_ML: 0,
      WINNER: 0,
      GOALS: 0,
      BTTS: 0,
      HANDICAPS: 0,
      CORNERS: 0,
      CARDS: 0,
      OTHER: 0,
    };

    sortedPicks.forEach((p) => {
      // Check Top ML condition: MUST have "ML Confianza Alta" tag from backend
      // This ensures strictly ML recommended picks (>70% confidence)
      if (p.reasoning && p.reasoning.includes("ML Confianza Alta")) {
        counts.TOP_ML++;
      }

      const cat = getPickCategory(p.market_type);
      if (cat in counts) {
        counts[cat as keyof typeof counts]++;
      } else {
        counts.OTHER++;
      }
    });
    return counts;
  }, [sortedPicks]);

  // Auto-select TOP_ML if available and not yet initialized
  useEffect(() => {
    if (!loading && !initialized && sortedPicks.length > 0) {
      if (categoryCounts.TOP_ML > 0) {
        setCurrentTab("TOP_ML");
      }
      setInitialized(true);
    }
  }, [loading, initialized, categoryCounts, sortedPicks.length]);

  // Filtered picks based on tab
  const filteredPicks = useMemo(() => {
    if (currentTab === "ALL") return sortedPicks;

    if (currentTab === "TOP_ML") {
      // Filter strictly for ML High Confidence picks
      return sortedPicks.filter(
        (p) => p.reasoning && p.reasoning.includes("ML Confianza Alta")
      );
    }

    return sortedPicks.filter(
      (p) => getPickCategory(p.market_type) === currentTab
    );
  }, [sortedPicks, currentTab]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: string) => {
    setCurrentTab(newValue);
  };

  if (loading) {
    return (
      <Box display="flex" alignItems="center" justifyContent="center" py={3}>
        <CircularProgress size={24} color="secondary" sx={{ mr: 1 }} />
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.6)" }}>
          Cargando picks...
        </Typography>
      </Box>
    );
  }

  // Only show error if we truly have NO picks (neither from API nor fallback)
  if (
    (error && sortedPicks.length === 0) ||
    (sortedPicks.length === 0 && !loading)
  ) {
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
    <Box>
      <Tabs
        value={currentTab}
        onChange={handleTabChange}
        variant="scrollable"
        scrollButtons="auto"
        textColor="secondary"
        indicatorColor="secondary"
        sx={{
          mb: 2,
          minHeight: 36,
          "& .MuiTab-root": {
            minHeight: 36,
            fontSize: "0.75rem",
            fontWeight: 600,
            color: "rgba(255,255,255,0.6)",
            textTransform: "none",
            "&.Mui-selected": {
              color: "#10b981", // Neon Green
            },
          },
          "& .MuiTabs-indicator": {
            backgroundColor: "#10b981", // Neon Green
          },
        }}
      >
        {/* Reordered: TOP_ML first if available, then ALL */}
        {categoryCounts.TOP_ML > 0 && (
          <Tab
            value="TOP_ML"
            label="🔥 Top ML"
            sx={{ color: "#fbbf24 !important" }}
          />
        )}
        <Tab value="ALL" label="Todos" />
        {categoryCounts.WINNER > 0 && <Tab value="WINNER" label="Ganador" />}
        {categoryCounts.GOALS > 0 && <Tab value="GOALS" label="Goles" />}
        {categoryCounts.BTTS > 0 && <Tab value="BTTS" label="Ambos Marcan" />}
        {categoryCounts.HANDICAPS > 0 && (
          <Tab value="HANDICAPS" label="Hándicaps" />
        )}
        {categoryCounts.CORNERS > 0 && <Tab value="CORNERS" label="Córners" />}
        {categoryCounts.CARDS > 0 && <Tab value="CARDS" label="Tarjetas" />}
      </Tabs>

      <Box
        sx={{
          maxHeight: { xs: "50vh", md: "400px" }, // Responsive max-height
          minHeight: "150px", // Allow it to shrink but keep some substance
          overflowY: "auto",
          pr: 1,
          // Custom Scrollbar
          "&::-webkit-scrollbar": {
            width: "6px",
          },
          "&::-webkit-scrollbar-track": {
            background: "rgba(255, 255, 255, 0.05)",
          },
          "&::-webkit-scrollbar-thumb": {
            background: "rgba(255, 255, 255, 0.2)",
            borderRadius: "4px",
          },
          "&::-webkit-scrollbar-thumb:hover": {
            background: "rgba(255, 255, 255, 0.3)",
          },
        }}
      >
        {filteredPicks.length > 0 ? (
          filteredPicks.map((pick, index) => (
            <PickRow key={`pick-${currentTab}-${index}`} pick={pick} />
          ))
        ) : (
          <Box py={4} textAlign="center">
            <Typography variant="caption" color="text.secondary">
              No hay picks en esta categoría
            </Typography>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default SuggestedPicksTab;

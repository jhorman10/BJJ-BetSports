import React, { useEffect, useState, useMemo, memo } from "react";
import {
  Box,
  Typography,
  Chip,
  CircularProgress,
  Tabs,
  Tab,
} from "@mui/material";
import { TipsAndUpdates, CheckCircle, Cancel, HourglassEmpty } from "@mui/icons-material";

import { MatchPrediction, SuggestedPick } from "../../../types";
import { generateFallbackPicks } from "../../../utils/predictionUtils";
import {
  getPickColor,
  getMarketIcon,
  getUniquePicks,
  getMarketCategory,
} from "../../../utils/marketUtils";
import { evaluatePickLive } from "../../../utils/pickValidationUtils";
import { useCacheStore } from "../../../application/stores/useCacheStore";
import { Match } from "../../../domain/entities/match";

interface SuggestedPicksTabProps {
  matchPrediction: MatchPrediction;
  onPicksCount?: (count: number) => void;
}

/**
 * Single row pick item - compact design
 */
const PickRow: React.FC<{ pick: SuggestedPick; match?: Match }> = memo(({ pick, match }) => {
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
          {(() => {
            if (!match) return null;
            const status = evaluatePickLive(pick, match);
            if (status === 'WON') return <CheckCircle color="success" sx={{ fontSize: "1rem", ml: 0.5 }} />;
            if (status === 'LOST') return <Cancel color="error" sx={{ fontSize: "1rem", ml: 0.5 }} />;
            if (status === 'PENDING') return <HourglassEmpty color="warning" sx={{ fontSize: "1rem", ml: 0.5 }} />;
            return null;
          })()}

          {/* INLINE IA CONFIRMED BADGE */}
          {pick.is_ia_confirmed && (
            <Chip
              label="IA CONFIRMED"
              size="small"
              sx={{
                ml: 1,
                bgcolor: "rgba(37, 99, 235, 0.15)",
                color: "#60a5fa",
                borderColor: "#60a5fa",
                borderWidth: "1px",
                borderStyle: "solid",
                fontWeight: 900,
                fontSize: "0.65rem",
                height: 20,
                boxShadow: "0 0 8px rgba(37, 99, 235, 0.3)",
                "& .MuiChip-label": { px: 1 },
              }}
            />
          )}

          {/* INLINE ML Alta Confianza BADGE */}
          {!pick.is_ia_confirmed &&
            (pick.is_ml_confirmed ||
              (pick.ml_confidence !== undefined && pick.ml_confidence > 0.7) ||
              (pick.reasoning && pick.reasoning.includes("ML"))) && (
              <Chip
                label="ML Alta Confianza"
                size="small"
                sx={{
                  ml: 1,
                  bgcolor: "rgba(56, 189, 248, 0.15)",
                  color: "#38bdf8",
                  borderColor: "#38bdf8",
                  borderWidth: "1px",
                  borderStyle: "solid",
                  fontWeight: 700,
                  fontSize: "0.65rem",
                  height: 20,
                  "& .MuiChip-label": { px: 1 },
                }}
              />
            )}
        </Box>
        {pick.expected_value !== undefined && pick.expected_value > 0 && (
          <Chip
            label={`EV: +${pick.expected_value.toFixed(1)}%`}
            size="small"
            sx={{
              mr: 1,
              bgcolor: "rgba(245, 158, 11, 0.5)",
              color: "#ffffff",
              fontWeight: 700,
              fontSize: "0.70rem",
              height: 24,
              border: "1px solid #f59e0b",
              "& .MuiChip-label": { px: 1 },
            }}
          />
        )}
        {pick.suggested_stake !== undefined && pick.suggested_stake > 0 && (
          <Chip
            label={`Stake: ${pick.suggested_stake.toFixed(2)}u`}
            size="small"
            sx={{
              mr: 1,
              bgcolor: "rgba(14, 165, 233, 0.5)",
              color: "#ffffff",
              fontWeight: 700,
              fontSize: "0.70rem",
              height: 24,
              border: "1px solid #0ea5e9",
              "& .MuiChip-label": { px: 1 },
            }}
          />
        )}
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

      {/* 3. Reasoning Text */}
      {(pick.formatted_reasoning || pick.reasoning) && (
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
            lineHeight: 1.4,
          }}
        >
          {(() => {
            // Clean the reasoning text
            let text = pick.formatted_reasoning || pick.reasoning || "";
            // Remove redundant tags if present (including those with emojis)
            text = text.replace(/\[.*IA CONFIRMED\]/g, "").trim();
            text = text.replace(/\[.*TOP ML\]/g, "").trim();
            text = text.replace(/\[.*ML ALTA CONFIANZA\]/g, "").trim();
            text = text.replace(/\[.*NORMAL\]/g, "").trim();
            // Remove leading/trailing punctuation/whitespace left over
            text = text.replace(/^[,.\s:]+|[,.\s:]+$/g, "");
            return text;
          })()}
        </Typography>
      )}
    </>
  );
});

/**
 * Suggested Picks Tab Component
 * Separated by tabs: Top ML, Winner, Goals, Corners, Cards, Others
 */
const SuggestedPicksTab: React.FC<SuggestedPicksTabProps> = ({
  matchPrediction,
  onPicksCount,
}) => {
  const { match } = matchPrediction;

  // Priority 1: Inline picks already in the prediction (from backend merge)
  const inlinePicks = matchPrediction.prediction?.suggested_picks;
  const hasInlinePicks = inlinePicks && inlinePicks.length > 0;

  // Priority 2: JIT cache fetch (fallback for daily matches with backend IDs)
  const { getPicks, prefetchMatch, isFetching } = useCacheStore();
  const cachedPicks = hasInlinePicks ? null : getPicks(match.id);
  const isLoading = hasInlinePicks ? false : isFetching(match.id);
  const hasPicks = hasInlinePicks || (cachedPicks && cachedPicks.length > 0);

  // Only trigger JIT fetch if we don't have inline picks AND cache is empty
  useEffect(() => {
    if (!hasInlinePicks && !hasPicks && !isLoading) {
      prefetchMatch(match.id);
    }
  }, [match.id, hasInlinePicks, hasPicks, isLoading, prefetchMatch]);

  const [currentTab, setCurrentTab] = useState("");
  const [initialized, setInitialized] = useState(false);

  const loading = isLoading && !hasPicks;
  const error = !hasPicks && !isLoading ? "No suggested picks available" : null;
  const resolvedPicks = hasInlinePicks ? inlinePicks : cachedPicks;
  const apiPicks = useMemo(
    () => (resolvedPicks ? { suggested_picks: resolvedPicks } : null),
    [resolvedPicks],
  );

  // Sort picks by probability (highest first)
  const sortedPicks = useMemo(() => {
    let picks = apiPicks?.suggested_picks ? [...apiPicks.suggested_picks] : [];

    // If API failed or returned explicit empty list, and we have prediction data, GENERATE FALLBACKS
    if ((!picks || picks.length === 0) && matchPrediction.prediction) {
      picks = generateFallbackPicks(matchPrediction);
    }

    picks = getUniquePicks(picks);
    return picks.sort((a, b) => {
      // 1. IA CONFIRMED
      if (a.is_ia_confirmed && !b.is_ia_confirmed) return -1;
      if (!a.is_ia_confirmed && b.is_ia_confirmed) return 1;
      // 2. Probability
      return b.probability - a.probability;
    });
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
      DOUBLE_CHANCE: 0,
      GOALS: 0,
      BTTS: 0,
      HANDICAPS: 0,
      CORNERS: 0,
      CARDS: 0,
      OTHER: 0,
    };

    sortedPicks.forEach((p) => {
      // Check Top ML condition
      const isTopML =
        p.is_ia_confirmed ||
        p.is_ml_confirmed ||
        (p.ml_confidence !== undefined && p.ml_confidence >= 0.85) ||
        (p.reasoning && p.reasoning.includes("ML Confianza Alta")) ||
        (p.reasoning && p.reasoning.includes("IA CONFIRMED"));

      if (isTopML) {
        counts.TOP_ML++;
        // If it's a Top ML pick, specifically EXCLUDE it from standard categories
        // per user request "Cuando un pick esta en el top ml, ya no debe aprecer en los demas tabs"
        return;
      }

      const cat = getMarketCategory(p.market_type);
      if (cat in counts) {
        counts[cat as keyof typeof counts]++;
      } else {
        counts.OTHER++;
      }
    });
    return counts;
  }, [sortedPicks]);

  // Auto-select first available tab in priority order
  const defaultTab = useMemo(() => {
    if (loading || sortedPicks.length === 0) return "";
    const priorityOrder = [
      "TOP_ML",
      "GOALS",
      "CORNERS",
      "CARDS",
      "BTTS",
      "WINNER",
      "DOUBLE_CHANCE",
      "HANDICAPS",
    ];

    for (const cat of priorityOrder) {
      if (categoryCounts[cat as keyof typeof categoryCounts] > 0) return cat;
    }
    return "";
  }, [loading, sortedPicks.length, categoryCounts]);

  // Initialize tab selection after first render to avoid state-update-during-render
  useEffect(() => {
    if (!initialized) {
      if (defaultTab && !currentTab) {
        queueMicrotask(() => {
          setCurrentTab(defaultTab);
          setInitialized(true);
        });
      } else if (!loading && sortedPicks.length === 0) {
        queueMicrotask(() => setInitialized(true));
      }
    }
  }, [defaultTab, loading, sortedPicks.length, initialized, currentTab]);

  // Filtered picks based on tab
  const filteredPicks = useMemo(() => {
    // Helper to check if a pick is considered "Top ML"
    const isTopML = (p: SuggestedPick): boolean =>
      Boolean(
        p.is_ia_confirmed ||
        p.is_ml_confirmed ||
        (p.ml_confidence !== undefined && p.ml_confidence >= 0.85) ||
        (p.reasoning && p.reasoning.includes("ML Confianza Alta")) ||
        (p.reasoning && p.reasoning.includes("IA CONFIRMED"))
      );

    if (currentTab === "TOP_ML") {
      // Filter strictly for ML High Confidence picks
      return sortedPicks.filter(isTopML);
    }

    // For other tabs, EXCLUDE Top ML picks
    return sortedPicks.filter(
      (p) => getMarketCategory(p.market_type) === currentTab && !isTopML(p)
    );
  }, [sortedPicks, currentTab]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: string): void => {
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
        value={currentTab || false}
        onChange={handleTabChange}
        variant="scrollable"
        scrollButtons="auto"
        textColor="secondary"
        indicatorColor="secondary"
        sx={{
          mb: 2,
          minHeight: 36,
          ml: 0,
          pl: 0,
          width: "100%",
          "& .MuiTabs-root": {
            ml: 0,
            pl: 0,
          },
          "& .MuiTabs-scroller": {
            ml: 0,
            pl: 0,
          },
          // Hide disabled scroll buttons to prevent shift
          "& .MuiTabs-scrollButtons.Mui-disabled": {
            width: 0,
            display: "none",
          },
          // Ensure tabs start from left
          "& .MuiTabs-flexContainer": {
            justifyContent: "flex-start",
          },
          "& .MuiTab-root": {
            minHeight: 36,
            minWidth: "auto", // Allow compact tabs
            px: 1.5,
            fontSize: "0.75rem",
            fontWeight: 600,
            color: "rgba(255,255,255,0.6)",
            textTransform: "none",
            ml: 0,
            // Align first tab flush left
            "&:first-of-type": {
              pl: 0,
              ml: 0,
            },
            "&.Mui-selected": {
              color: "#10b981", // Neon Green
            },
          },
          "& .MuiTabs-indicator": {
            backgroundColor: "#10b981", // Neon Green
          },
        }}
      >
        {/* Ordered Tabs: Top ML | Goles | Corners | Tarjetas | Ambos marcan | Ganador | Handicap */}
        {categoryCounts.TOP_ML > 0 && (
          <Tab
            value="TOP_ML"
            label="🔥 Top ML"
            sx={{ color: "#fbbf24 !important" }}
          />
        )}
        {categoryCounts.GOALS > 0 && <Tab value="GOALS" label="Goles" />}
        {categoryCounts.CORNERS > 0 && <Tab value="CORNERS" label="Córners" />}
        {categoryCounts.CARDS > 0 && <Tab value="CARDS" label="Tarjetas" />}
        {categoryCounts.BTTS > 0 && <Tab value="BTTS" label="Ambos Marcan" />}
        {categoryCounts.WINNER > 0 && <Tab value="WINNER" label="Ganador" />}
        {categoryCounts.DOUBLE_CHANCE > 0 && (
          <Tab value="DOUBLE_CHANCE" label="Doble Oportunidad" />
        )}
        {categoryCounts.HANDICAPS > 0 && (
          <Tab value="HANDICAPS" label="Hándicaps" />
        )}
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
           filteredPicks.map((pick) => (
            <PickRow key={pick.market_type} pick={pick} match={match} />
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

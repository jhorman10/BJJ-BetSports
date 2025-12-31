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
  if (
    type.includes("GOAL") ||
    type.includes("BTTS") ||
    type.includes("OVER") ||
    type.includes("UNDER")
  ) {
    return "GOALS";
  }
  if (
    type.includes("WIN") ||
    type.includes("DRAW") ||
    type.includes("CHANCE") ||
    type.includes("HANDICAP")
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
  const [loading, setLoading] = useState(true);
  const [apiPicks, setApiPicks] = useState<MatchSuggestedPicks | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Initialize with ALL, but we will try to switch to TOP_ML if available
  const [currentTab, setCurrentTab] = useState("ALL");
  const [initialized, setInitialized] = useState(false);

  // Fetch picks from backend API with localStorage caching
  useEffect(() => {
    const CACHE_KEY = `suggested-picks-${match.id}`;
    const CACHE_TTL = 30 * 60 * 1000; // 30 minutes

    const fetchPicks = async () => {
      try {
        const cached = localStorage.getItem(CACHE_KEY);
        if (cached) {
          try {
            const { data, timestamp } = JSON.parse(cached);

            // Check if backend data is newer than cache
            const backendDate = matchPrediction.prediction.data_updated_at
              ? new Date(matchPrediction.prediction.data_updated_at).getTime()
              : 0;

            const isCacheFresh = Date.now() - timestamp < CACHE_TTL;
            const isCacheNewerThanBackend = timestamp > backendDate;

            if (isCacheFresh && isCacheNewerThanBackend) {
              console.log("Using cached picks (Fresh & Newer than backend)");
              setApiPicks(data);
              setLoading(false);
              return;
            } else {
              console.log("Cache invalid: ", {
                fresh: isCacheFresh,
                newer: isCacheNewerThanBackend,
                cacheTime: new Date(timestamp).toISOString(),
                backendTime: matchPrediction.prediction.data_updated_at,
              });
              // Show outdated while fetching
              setApiPicks(data);
            }
          } catch (e) {
            console.error("Cache parse error", e);
          }
        } else {
          setLoading(true);
        }

        setError(null);
        const data = await api.getSuggestedPicks(match.id);
        setApiPicks(data);

        localStorage.setItem(
          CACHE_KEY,
          JSON.stringify({
            data,
            timestamp: Date.now(),
          })
        );
      } catch (err: any) {
        if (!apiPicks) {
          // Only set error if we don't have cached data
          if (err.response && err.response.status === 404) {
            setError("Datos insuficientes para generar picks");
          } else {
            setError("No se pudieron cargar los picks");
          }
        }
      } finally {
        setLoading(false);
      }
    };

    fetchPicks();
  }, [match.id]);

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
        {categoryCounts.CORNERS > 0 && <Tab value="CORNERS" label="Córners" />}
        {categoryCounts.CARDS > 0 && <Tab value="CARDS" label="Tarjetas" />}
      </Tabs>

      <Box sx={{ maxHeight: "350px", overflowY: "auto", pr: 0.5 }}>
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

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
    // "OVER" and "UNDER" can be corners/cards too, but typically if it's not corner/card specific it's goals
    // Wait, OVER_CORNERS contains "OVER". Order matters.
    // Checked CORNER/CARD first.
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
 * Separated by tabs: Winner, Goals, Corners, Cards, Others
 */
const SuggestedPicksTab: React.FC<SuggestedPicksTabProps> = ({
  matchPrediction,
  onPicksCount,
}) => {
  const { match } = matchPrediction;
  const [loading, setLoading] = useState(true);
  const [apiPicks, setApiPicks] = useState<MatchSuggestedPicks | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentTab, setCurrentTab] = useState("ALL");

  // Fetch picks from backend API with localStorage caching
  useEffect(() => {
    const CACHE_KEY = `suggested-picks-${match.id}`;
    const CACHE_TTL = 30 * 60 * 1000; // 30 minutes

    const fetchPicks = async () => {
      try {
        // 1. Try to load from localStorage first (instant)
        const cached = localStorage.getItem(CACHE_KEY);
        if (cached) {
          try {
            const { data, timestamp } = JSON.parse(cached);
            const age = Date.now() - timestamp;

            // Show cached data immediately
            setApiPicks(data);
            setLoading(false);

            // If cache is still fresh (< 30min), skip API call
            if (age < CACHE_TTL) {
              return;
            }
          } catch (e) {
            // Invalid cache, continue to fetch
          }
        } else {
          // No cache, show loading
          setLoading(true);
        }

        // 2. Fetch fresh data from API (in background if cache exists)
        setError(null);
        const data = await api.getSuggestedPicks(match.id);
        setApiPicks(data);

        // 3. Update localStorage
        localStorage.setItem(
          CACHE_KEY,
          JSON.stringify({
            data,
            timestamp: Date.now(),
          })
        );
      } catch (err: any) {
        if (err.response && err.response.status === 404) {
          setError("Datos insuficientes para generar picks");
        } else {
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

    // Fallback Frontend
    if (picks.length === 0 && matchPrediction.prediction) {
      picks = generateFallbackPicks(matchPrediction);
    }

    // Filter duplicates
    picks = getUniquePicks(picks);

    // Sort by probability (highest first)
    return picks.sort((a, b) => b.probability - a.probability);
  }, [apiPicks, matchPrediction]);

  // Report count
  useEffect(() => {
    if (onPicksCount) {
      onPicksCount(sortedPicks.length);
    }
  }, [sortedPicks.length, onPicksCount]);

  // Filtered picks based on tab
  const filteredPicks = useMemo(() => {
    if (currentTab === "ALL") return sortedPicks;
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
              color: "#22c55e",
            },
          },
          "& .MuiTabs-indicator": {
            backgroundColor: "#22c55e",
          },
        }}
      >
        <Tab value="ALL" label="Todos" />
        <Tab value="WINNER" label="Ganador" />
        <Tab value="GOALS" label="Goles" />
        <Tab value="CORNERS" label="Córners" />
        <Tab value="CARDS" label="Tarjetas" />
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

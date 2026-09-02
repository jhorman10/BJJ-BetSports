import React, { useEffect, useLayoutEffect, useState, useMemo } from "react";
import {
  Box,
  Typography,
  CircularProgress,
} from "@mui/material";
import { TipsAndUpdates } from "@mui/icons-material";

import { MatchPrediction, SuggestedPick } from "../../../types";
import { generateFallbackPicks } from "../../../utils/predictionUtils";
import {
  getUniquePicks,
  getMarketCategory,
} from "../../../utils/marketUtils";
import { useCacheStore } from "../../../application/stores/useCacheStore";

import CategoryTabs from "./components/CategoryTabs";
import PicksScrollList from "./components/PicksScrollList";

interface SuggestedPicksTabProps {
  matchPrediction: MatchPrediction;
  onPicksCount?: (count: number) => void;
}

const isTopMLPick = (p: SuggestedPick): boolean =>
  Boolean(
    p.is_ia_confirmed ||
    p.is_ml_confirmed ||
    (p.ml_confidence !== undefined && p.ml_confidence >= 0.85) ||
    (p.reasoning && /ML (ALTA CONFIANZA|Confianza Alta)/i.test(p.reasoning)) ||
    (p.reasoning && /IA CONFIRMED/i.test(p.reasoning))
  );

const uniqueByMarket = (picks: SuggestedPick[]): SuggestedPick[] => {
  const seen = new Set<string>();
  const unique: SuggestedPick[] = [];
  for (const pick of picks) {
    if (seen.has(pick.market_type)) continue;
    seen.add(pick.market_type);
    unique.push(pick);
  }
  return unique;
};

const SuggestedPicksTab: React.FC<SuggestedPicksTabProps> = ({
  matchPrediction,
  onPicksCount,
}) => {
  const { match } = matchPrediction;
  const inlinePicks = matchPrediction.prediction?.suggested_picks;
  const hasInlinePicks = inlinePicks && inlinePicks.length > 0;

  const { getPicks, prefetchMatch, isFetching } = useCacheStore();
  const cachedPicks = hasInlinePicks ? null : getPicks(match.id);
  const isLoading = hasInlinePicks ? false : isFetching(match.id);
  const hasPicks = hasInlinePicks || (cachedPicks && cachedPicks.length > 0);

  useEffect(() => {
    if (!hasInlinePicks && !hasPicks && !isLoading) {
      prefetchMatch(match.id);
    }
  }, [match.id, hasInlinePicks, hasPicks, isLoading, prefetchMatch]);

  const [tabSelection, setTabSelection] = useState<{
    matchId: string;
    tab: string;
  }>({ matchId: match.id, tab: "" });

  const currentTab = tabSelection.matchId === match.id ? tabSelection.tab : "";
  const loading = isLoading && !hasPicks;
  const error = !hasPicks && !isLoading ? "No suggested picks available" : null;
  const resolvedPicks = hasInlinePicks ? inlinePicks : cachedPicks;
  const apiPicks = useMemo(
    () => (resolvedPicks ? { suggested_picks: resolvedPicks } : null),
    [resolvedPicks],
  );

  const sortedPicks = useMemo(() => {
    let picks = apiPicks?.suggested_picks ? [...apiPicks.suggested_picks] : [];
    if ((!picks || picks.length === 0) && matchPrediction.prediction) {
      picks = generateFallbackPicks(matchPrediction);
    }
    picks = getUniquePicks(picks);
    return picks.sort((a, b) => {
      if (a.is_ia_confirmed && !b.is_ia_confirmed) return -1;
      if (!a.is_ia_confirmed && b.is_ia_confirmed) return 1;
      return b.probability - a.probability;
    });
  }, [apiPicks, matchPrediction]);

  const uniquePickCount = useMemo(
    () => uniqueByMarket(sortedPicks).length,
    [sortedPicks],
  );

  useLayoutEffect(() => {
    if (onPicksCount) onPicksCount(uniquePickCount);
  }, [uniquePickCount, onPicksCount]);

  const topMLMarketTypes = useMemo(() => {
    const marketTypes = new Set<string>();
    sortedPicks.forEach((p) => {
      if (isTopMLPick(p)) marketTypes.add(p.market_type);
    });
    return marketTypes;
  }, [sortedPicks]);

  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = {
      TOP_ML: 0, WINNER: 0, DOUBLE_CHANCE: 0, GOALS: 0,
      BTTS: 0, HANDICAPS: 0, CORNERS: 0, CARDS: 0, OTHER: 0,
    };
    const countedMarkets = new Set<string>();
    sortedPicks.forEach((p) => {
      if (countedMarkets.has(p.market_type)) return;
      countedMarkets.add(p.market_type);
      if (topMLMarketTypes.has(p.market_type)) { counts.TOP_ML++; return; }
      const cat = getMarketCategory(p.market_type);
      if (cat in counts) counts[cat]++; else counts.OTHER++;
    });
    return counts;
  }, [sortedPicks, topMLMarketTypes]);

  const defaultTab = useMemo(() => {
    if (loading || sortedPicks.length === 0) return "";
    const priorityOrder = ["TOP_ML", "GOALS", "CORNERS", "CARDS", "BTTS", "WINNER", "DOUBLE_CHANCE", "HANDICAPS"];
    for (const cat of priorityOrder) {
      if (categoryCounts[cat] > 0) return cat;
    }
    return "";
  }, [loading, sortedPicks.length, categoryCounts]);

  const safeTab =
    currentTab && categoryCounts[currentTab] > 0 ? currentTab : "";
  const activeTab = safeTab || defaultTab;

  const filteredPicks = useMemo(() => {
    if (activeTab === "TOP_ML") {
      return uniqueByMarket(sortedPicks.filter(isTopMLPick));
    }
    return uniqueByMarket(
      sortedPicks.filter(
        (p) =>
          getMarketCategory(p.market_type) === activeTab &&
          !topMLMarketTypes.has(p.market_type)
      )
    );
  }, [sortedPicks, activeTab, topMLMarketTypes]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: string): void => {
    setTabSelection({ matchId: match.id, tab: newValue });
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

  if (
    (error && sortedPicks.length === 0) ||
    (sortedPicks.length === 0 && !loading)
  ) {
    return (
      <Box display="flex" alignItems="center" justifyContent="center" py={2}>
        <TipsAndUpdates sx={{ fontSize: 24, color: "rgba(255,255,255,0.3)", mr: 1 }} />
        <Typography variant="body2" sx={{ color: "rgba(255,255,255,0.5)" }}>
          {error || "Sin picks disponibles"}
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <CategoryTabs
        activeTab={activeTab}
        categoryCounts={categoryCounts}
        onTabChange={handleTabChange}
      />
      <PicksScrollList filteredPicks={filteredPicks} match={match} />
    </Box>
  );
};

export default SuggestedPicksTab;

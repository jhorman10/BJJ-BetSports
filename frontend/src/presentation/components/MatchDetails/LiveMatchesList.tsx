import React, { useCallback, useMemo } from "react";
import LiveMatchesView from "./LiveMatchesView";
import { useLiveStore } from "../../../application/stores/useLiveStore";
import { useUIStore } from "../../../application/stores/useUIStore";
import { usePredictionStore } from "../../../application/stores/usePredictionStore";
import {
  matchLiveWithPrediction,
  LiveMatchRaw,
} from "../../../utils/matchMatching";

interface LiveMatchesListProps {
  selectedLeagueIds?: string[];
  selectedLeagueNames?: string[];
}

const LiveMatchesList: React.FC<LiveMatchesListProps> = ({
  selectedLeagueIds = [],
  selectedLeagueNames = [],
}) => {
  const { matches, loading, error, fetchMatches } = useLiveStore();
  const { openLiveMatchModal } = useUIStore();
  const { predictions } = usePredictionStore();

  // Convert LiveMatchPrediction to LiveMatch format expected by LiveMatchesView
  // Using useMemo for optimized recalculation
  const liveMatches = useMemo(() => {
    return matches.map((m) => ({
      id: m.match.id,
      home_team: m.match.home_team.name,
      home_short_name: m.match.home_team.short_name,
      away_team: m.match.away_team.name,
      away_short_name: m.match.away_team.short_name,
      home_score: m.match.home_goals ?? 0,
      away_score: m.match.away_goals ?? 0,
      status: m.match.status || "LIVE",
      minute: m.match.minute || "", // Use minute from match data
      league_id: m.match.league?.id || "",
      league_name: m.match.league?.name || "",
      league_flag: m.match.league?.flag || "",
      home_corners: m.match.home_corners ?? 0,
      away_corners: m.match.away_corners ?? 0,
      home_yellow_cards: m.match.home_yellow_cards ?? 0,
      away_yellow_cards: m.match.away_yellow_cards ?? 0,
      home_red_cards: m.match.home_red_cards ?? 0,
      away_red_cards: m.match.away_red_cards ?? 0,
      home_logo_url: m.match.home_team.logo_url,
      away_logo_url: m.match.away_team.logo_url,
      prediction: m.prediction,
    }));
  }, [matches]);

  const handleMatchClick = useCallback(
    (liveMatch: LiveMatchRaw) => {
      const matchPrediction = matchLiveWithPrediction(liveMatch, predictions);
      openLiveMatchModal(matchPrediction);
    },
    [predictions, openLiveMatchModal]
  );

  return (
    <LiveMatchesView
      matches={liveMatches}
      loading={loading}
      error={error}
      onRefresh={fetchMatches}
      selectedLeagueIds={selectedLeagueIds}
      selectedLeagueNames={selectedLeagueNames}
      onMatchClick={handleMatchClick}
    />
  );
};

export default LiveMatchesList;

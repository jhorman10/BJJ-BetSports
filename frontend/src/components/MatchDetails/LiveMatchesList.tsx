import React from "react";
import { useLiveMatches } from "../../hooks/useLiveMatches";
import LiveMatchesView from "./LiveMatchesView";

interface LiveMatchesListProps {
  selectedLeagueIds?: string[];
  selectedLeagueNames?: string[];
  onMatchSelect?: (matchId: string) => void;
}

const LiveMatchesList: React.FC<LiveMatchesListProps> = ({
  selectedLeagueIds = [],
  selectedLeagueNames = [],
  onMatchSelect,
}) => {
  const { matches, loading, error, refresh } = useLiveMatches();

  return (
    <LiveMatchesView
      matches={matches}
      loading={loading}
      error={error}
      onRefresh={refresh}
      selectedLeagueIds={selectedLeagueIds}
      selectedLeagueNames={selectedLeagueNames}
      onMatchSelect={onMatchSelect}
    />
  );
};

export default LiveMatchesList;

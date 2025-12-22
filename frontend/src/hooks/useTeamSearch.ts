import { useState, useEffect } from "react";
import api from "../services/api";
import { MatchPrediction } from "../types";

export function useTeamSearch() {
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [searchMatches, setSearchMatches] = useState<MatchPrediction[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const delayDebounceFn = setTimeout(async () => {
      if (searchQuery.length > 2) {
        setLoading(true);
        try {
          const matches = await api.getTeamMatches(searchQuery);
          // Transform API Match to MatchPrediction structure
          // Note: This transformation logic mimics what was in App.tsx
          // In a real app, this might be unified in the service or a helper
          const predictions: MatchPrediction[] = matches.map((m) => ({
            match: m,
            prediction: {
              match_id: m.id,
              confidence: 0,
              home_win_probability: 0,
              draw_probability: 0,
              away_win_probability: 0,
              over_25_probability: 0,
              under_25_probability: 0,
              predicted_home_goals: 0,
              predicted_away_goals: 0,
              recommended_bet: "N/A",
              over_under_recommendation: "N/A",
              data_sources: [],
              created_at: new Date().toISOString(),
            },
          }));
          setSearchMatches(predictions);
        } catch (e) {
          console.error(e);
          setSearchMatches([]);
        } finally {
          setLoading(false);
        }
      } else {
        setSearchMatches([]);
      }
    }, 1000);

    return () => clearTimeout(delayDebounceFn);
  }, [searchQuery]);

  const resetSearch = () => {
    setSearchQuery("");
    setSearchMatches([]);
    setLoading(false);
  };

  return {
    searchQuery,
    setSearchQuery,
    searchMatches,
    loading,
    resetSearch,
  };
}

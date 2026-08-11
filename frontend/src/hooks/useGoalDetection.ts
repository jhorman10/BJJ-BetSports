import { useEffect, useRef } from "react";

import { useUIStore } from "../application/stores/useUIStore";
import { useLiveStore } from "../application/stores/useLiveStore";

export const useGoalDetection = (): {
  goalToast: { open: boolean; message: string };
  closeGoalToast: () => void;
} => {
  const { showGoalToast, closeGoalToast, goalToast } = useUIStore();
  const { matches: liveMatches, loading: liveLoading } = useLiveStore();

  const prevScoresRef = useRef<Map<string, { home: number; away: number }>>(
    new Map()
  );

  useEffect(() => {
    if (liveLoading) return;

    let goalDetected = false;
    let message = "";

    liveMatches.forEach((matchPred) => {
      const match = matchPred.match;
      const prev = prevScoresRef.current.get(match.id);

      if (prev) {
        if ((match.home_goals ?? 0) > prev.home) {
          goalDetected = true;
          message = `⚽ ¡GOL de ${match.home_team.name}! (${match.home_goals}-${match.away_goals})`;
        } else if ((match.away_goals ?? 0) > prev.away) {
          goalDetected = true;
          message = `⚽ ¡GOL de ${match.away_team.name}! (${match.home_goals}-${match.away_goals})`;
        }
      }

      prevScoresRef.current.set(match.id, {
        home: match.home_goals ?? 0,
        away: match.away_goals ?? 0,
      });
    });

    if (goalDetected) {
      showGoalToast(message);
    }
  }, [liveMatches, liveLoading, showGoalToast]);

  return { goalToast, closeGoalToast };
};

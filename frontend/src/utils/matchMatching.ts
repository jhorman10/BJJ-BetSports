import { MatchPrediction } from "../domain/entities";
import { normalizeName } from "./searchUtils";

export interface LiveMatchRaw {
  id: string;
  home_team: string;
  home_short_name?: string;
  away_team: string;
  away_short_name?: string;
  league_id: string;
  league_name: string;
  league_flag?: string;
  home_score: number;
  away_score: number;
  status: string;
  minute?: string;
  home_corners: number;
  away_corners: number;
  home_yellow_cards: number;
  away_yellow_cards: number;
  home_red_cards: number;
  away_red_cards: number;
  home_logo_url?: string;
  away_logo_url?: string;
  prediction?: any;
}

export const matchLiveWithPrediction = (
  liveMatch: LiveMatchRaw,
  predictions: MatchPrediction[]
): MatchPrediction => {
  // 1. Try to use the prediction attached directly to the live match (from backend)
  let prediction = liveMatch.prediction;

  // 2. If no prediction, try to find it in our loaded predictions list (Frontend Matching)
  if (!prediction) {
    const foundPrediction = predictions.find((p) => {
      // Normalize: remove special chars, extra spaces, lowercase
      const pHome = normalizeName(p.match.home_team.name);
      const pAway = normalizeName(p.match.away_team.name);
      const lHome = normalizeName(liveMatch.home_team);
      const lAway = normalizeName(liveMatch.away_team);

      // Word-level matching for better flexibility (e.g. "Man City" vs "Manchester City")
      const wordsMatch = (str1: string, str2: string) => {
        const w1 = str1.split(" ").filter((w) => w.length > 2);
        const w2 = str2.split(" ").filter((w) => w.length > 2);
        if (w1.length > 0 && w2.length > 0) {
          return (
            w1.some((w) => str2.includes(w)) || w2.some((w) => str1.includes(w))
          );
        }
        return str1.includes(str2) || str2.includes(str1);
      };

      return wordsMatch(pHome, lHome) && wordsMatch(pAway, lAway);
    });

    if (foundPrediction) {
      prediction = foundPrediction.prediction;
    }
  }

  // Convert LiveMatch to MatchPrediction structure
  const matchPrediction: MatchPrediction = {
    match: {
      id: liveMatch.id,
      home_team: {
        id: "0",
        name: liveMatch.home_team,
        short_name: liveMatch.home_short_name,
        logo: "",
      },
      away_team: {
        id: "0",
        name: liveMatch.away_team,
        short_name: liveMatch.away_short_name,
        logo: "",
      },
      match_date: new Date().toISOString(),
      league: {
        id: liveMatch.league_id,
        name: liveMatch.league_name,
        country: "",
        flag: liveMatch.league_flag || "",
      },
      home_goals: liveMatch.home_score,
      away_goals: liveMatch.away_score,
      status: liveMatch.status,
      home_corners: liveMatch.home_corners,
      away_corners: liveMatch.away_corners,
      home_yellow_cards: liveMatch.home_yellow_cards,
      away_yellow_cards: liveMatch.away_yellow_cards,
      home_red_cards: liveMatch.home_red_cards,
      away_red_cards: liveMatch.away_red_cards,
    },
    prediction:
      prediction ||
      ({
        id: `live-${liveMatch.id}`,
        match_id: liveMatch.id,
        home_win_probability: 0,
        draw_probability: 0,
        away_win_probability: 0,
        confidence: 0,
        predicted_home_goals: 0,
        predicted_away_goals: 0,
        created_at: new Date().toISOString(),
      } as any),
  };

  return matchPrediction;
};

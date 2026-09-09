import { LiveMatch } from "../../../hooks/useLiveMatches";
import { Team, Match } from "../../../types";

export interface NormalizedMatch {
  status: string;
  leagueName: string;
  homeTeamName: string;
  awayTeamName: string;
  homeScore: number;
  awayScore: number;
  homeTeam?: Team | string;
  awayTeam?: Team | string;
}

export type MatchLike = (LiveMatch | Match) & {
  home_goals?: number;
  away_goals?: number;
  home_team_obj?: Team;
  away_team_obj?: Team;
};

export const normalizeMatch = (match: MatchLike): NormalizedMatch => {
  if ("league_name" in match) {
    const lm = match as LiveMatch;
    return {
      status: lm.status || "LIVE",
      leagueName: lm.league_name || "Liga",
      homeTeamName: typeof lm.home_team === "string" ? lm.home_team : lm.home_team.name || "Local",
      awayTeamName: typeof lm.away_team === "string" ? lm.away_team : lm.away_team.name || "Visitante",
      homeTeam: lm.home_team,
      awayTeam: lm.away_team,
      homeScore: lm.home_score ?? 0,
      awayScore: lm.away_score ?? 0,
    };
  } else {
    const m = match as Match & {
      home_goals?: number;
      away_goals?: number;
      home_team_obj?: Team;
      away_team_obj?: Team;
    };
    return {
      status: m.status || "LIVE",
      leagueName: (m && m.league && m.league.name) || "Liga",
      homeTeamName: m.home_team?.name || "Local",
      awayTeamName: m.away_team?.name || "Visitante",
      homeScore: m.home_goals ?? 0,
      awayScore: m.away_goals ?? 0,
      homeTeam: m.home_team,
      awayTeam: m.away_team,
    };
  }
};

import { SuggestedPick } from '../domain/entities/pick';
import { Match } from '../domain/entities/match';

export type PickStatus = 'WON' | 'LOST' | 'PENDING' | 'UNKNOWN';

/**
 * Valida un pick sugerido contra los datos en vivo del partido.
 * Implementa "Early Resolution" para mercados Over/Under.
 */
export const evaluatePickLive = (pick: SuggestedPick, match?: Match): PickStatus => {
  if (!match) return 'UNKNOWN';

  // Check if it already has a backend result
  if (pick.result === 'WIN' || pick.result === 'WON') return 'WON';
  if (pick.result === 'LOSS' || pick.result === 'LOST') return 'LOST';

  // Define what statuses mean finished (Common API responses: FT, Finished, Ended)
  const isFinished = ['FT', 'FINISHED', 'ENDED', 'AET', 'PEN'].includes((match.status || '').toUpperCase());
  
  // Parse threshold from pick_code (e.g., O2.5 -> 2.5) or market_label ("Más de 2.5 tarjetas")
  const extractThreshold = (str: string) => {
    const regexMatch = str.match(/(\d+\.\d+)/);
    return regexMatch ? parseFloat(regexMatch[1]) : 0;
  };

  const threshold = extractThreshold(pick.pick_code || pick.market_label || '');

  switch (pick.market_type) {
    case 'goals_over': {
      const currentGoals = (match.home_goals || 0) + (match.away_goals || 0);
      if (currentGoals > threshold) return 'WON';
      return isFinished ? 'LOST' : 'PENDING';
    }
    case 'goals_under': {
      const currentGoals = (match.home_goals || 0) + (match.away_goals || 0);
      if (currentGoals > threshold) return 'LOST';
      return isFinished ? 'WON' : 'PENDING';
    }
    case 'corners_over': {
      const currentCorners = (match.home_corners || 0) + (match.away_corners || 0);
      if (currentCorners > threshold) return 'WON';
      return isFinished ? 'LOST' : 'PENDING';
    }
    case 'corners_under': {
      const currentCorners = (match.home_corners || 0) + (match.away_corners || 0);
      if (currentCorners > threshold) return 'LOST';
      return isFinished ? 'WON' : 'PENDING';
    }
    case 'cards_over': {
      // Sum both yellow and red cards
      const currentCards = (match.home_yellow_cards || 0) + (match.away_yellow_cards || 0) + 
                           (match.home_red_cards || 0) + (match.away_red_cards || 0);
      if (currentCards > threshold) return 'WON';
      return isFinished ? 'LOST' : 'PENDING';
    }
    case 'cards_under': {
      const currentCards = (match.home_yellow_cards || 0) + (match.away_yellow_cards || 0) + 
                           (match.home_red_cards || 0) + (match.away_red_cards || 0);
      if (currentCards > threshold) return 'LOST';
      return isFinished ? 'WON' : 'PENDING';
    }
    case 'btts_yes': {
      if ((match.home_goals || 0) > 0 && (match.away_goals || 0) > 0) return 'WON';
      return isFinished ? 'LOST' : 'PENDING';
    }
    case 'btts_no': {
      if ((match.home_goals || 0) > 0 && (match.away_goals || 0) > 0) return 'LOST';
      return isFinished ? 'WON' : 'PENDING';
    }
    case 'winner': {
      if (!isFinished) return 'PENDING';
      const homeGoals = match.home_goals || 0;
      const awayGoals = match.away_goals || 0;
      if (pick.pick_code === '1' && homeGoals > awayGoals) return 'WON';
      if (pick.pick_code === '2' && awayGoals > homeGoals) return 'WON';
      if (pick.pick_code === 'X' && homeGoals === awayGoals) return 'WON';
      return 'LOST';
    }
    case 'double_chance': {
      if (!isFinished) return 'PENDING';
      const homeGoals = match.home_goals || 0;
      const awayGoals = match.away_goals || 0;
      if (pick.pick_code === '1X' && homeGoals >= awayGoals) return 'WON';
      if (pick.pick_code === 'X2' && awayGoals >= homeGoals) return 'WON';
      if (pick.pick_code === '12' && homeGoals !== awayGoals) return 'WON';
      return 'LOST';
    }
    default:
      return 'UNKNOWN';
  }
};

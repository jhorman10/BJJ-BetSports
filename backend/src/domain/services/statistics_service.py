"""
Statistics Domain Service

Handles calculation of team statistics from match history.
"""

from typing import List, Optional
from src.domain.entities.entities import Match, TeamStatistics

class StatisticsService:
    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize team name for comparison."""
        # Remove common prefixes/suffixes
        remove = ["fc", "cf", "as", "sc", "ac", "inter", "real", "sporting", "club", "de", "le", "la"]
        
        cleaned = name.lower()
        for word in remove:
            # Remove isolated occurrences
            cleaned = cleaned.replace(f" {word} ", " ")
            if cleaned.startswith(f"{word} "):
                cleaned = cleaned[len(word)+1:]
            if cleaned.endswith(f" {word}"):
                cleaned = cleaned[:-len(word)-1]
                
        return cleaned.strip().replace(" ", "")

    @staticmethod
    def _resolve_alias(name: str) -> str:
        """Resolve common team name aliases."""
        aliases = {
            "man city": "manchester city",
            "mancity": "manchester city",
            "man utd": "manchester united",
            "manutd": "manchester united",
            "man united": "manchester united",
            "spurs": "tottenham",
            "tottenham hotspur": "tottenham",
            "wolves": "wolverhampton",
            "wolverhampton wanderers": "wolverhampton",
            "nottm forest": "nottingham forest",
            "sheff utd": "sheffield united",
            "newcastle": "newcastle united",
            "brighton": "brighton hove albion",
            "west ham": "west ham united",
            "leicester": "leicester city",
            "leeds": "leeds city",
            "norwich": "norwich city",
            # Spain
            "ath madrid": "atletico madrid",
            "atl madrid": "atletico madrid",
            "r madrid": "real madrid",
            "sociedad": "real sociedad",
            "betis": "real betis",
            "celta": "celta vigo",
            "ath bilbao": "athletic club",
            "athletic bilbao": "athletic club",
            # Italy
            "inter": "inter milan",
            "internazionale": "inter milan",
            "ac milan": "milan",
            # Germany
            "bayern": "bayern munich",
            "dortmund": "borussia dortmund", 
            "leverkusen": "bayer leverkusen",
            "gladbach": "borussia monchengladbach",
            "frankfurt": "eintracht frankfurt",
        }
        normalized = name.lower().strip()
        if normalized in aliases:
            return aliases[normalized]
        # Check partials if needed, or return same
        return name

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize team name for comparison."""
        
        # 1. Resolve Aliases first
        name = StatisticsService._resolve_alias(name)
        
        # 2. Standard cleanup
        # Remove common prefixes/suffixes
        remove = ["fc", "cf", "as", "sc", "ac", "inter", "real", "sporting", "club", "de", "le", "la"]
        
        cleaned = name.lower()
        for word in remove:
            # Remove isolated occurrences
            cleaned = cleaned.replace(f" {word} ", " ")
            if cleaned.startswith(f"{word} "):
                cleaned = cleaned[len(word)+1:]
            if cleaned.endswith(f" {word}"):
                cleaned = cleaned[:-len(word)-1]
                
        return cleaned.strip().replace(" ", "")

    @staticmethod
    def calculate_team_statistics(
        team_name: str,
        matches: List[Match],
    ) -> TeamStatistics:
        """
        Calculate statistics for a team from match history.
        
        Args:
            team_name: Team name
            matches: List of historical matches
            
        Returns:
            TeamStatistics for the team
        """
        team_id: Optional[str] = None
        matches_played = 0
        wins = 0
        draws = 0
        losses = 0
        goals_scored = 0
        goals_conceded = 0
        home_wins = 0
        away_wins = 0
        
        # New stats for picks
        total_corners = 0
        total_yellow_cards = 0
        total_red_cards = 0
        
        recent_results = []
        
        target_norm = StatisticsService._normalize_name(team_name)
        
        for match in matches:
            if not match.is_played:
                continue
            
            home_norm = StatisticsService._normalize_name(match.home_team.name)
            away_norm = StatisticsService._normalize_name(match.away_team.name)
            
            # Check for match (exact normalized or containment if substantial)
            is_home = target_norm == home_norm or (len(target_norm) > 3 and target_norm in home_norm) or (len(home_norm) > 3 and home_norm in target_norm)
            is_away = target_norm == away_norm or (len(target_norm) > 3 and target_norm in away_norm) or (len(away_norm) > 3 and away_norm in target_norm)
            
            if not (is_home or is_away):
                continue
            
            if team_id is None:
                team_id = match.home_team.id if is_home else match.away_team.id
            
            matches_played += 1
            
            # Get stats based on role
            goals_for = match.home_goals if is_home else match.away_goals
            goals_against = match.away_goals if is_home else match.home_goals
            
            # Robustly handle None goals
            if goals_for is None or goals_against is None:
                continue
                
            goals_scored += goals_for
            goals_conceded += goals_against
            
            if goals_for > goals_against:
                wins += 1
                if is_home:
                    home_wins += 1
                else:
                    away_wins += 1
                recent_results.append('W')
            elif goals_for < goals_against:
                losses += 1
                recent_results.append('L')
            else:
                draws += 1
                recent_results.append('D')
                
            # Accumulate corners/cards
            if match.home_corners is not None and match.away_corners is not None:
                total_corners += match.home_corners if is_home else match.away_corners
                
            # Accumulate cards
            y_cards = match.home_yellow_cards if is_home else match.away_yellow_cards
            r_cards = match.home_red_cards if is_home else match.away_red_cards
            
            if y_cards is not None:
                total_yellow_cards += y_cards
            if r_cards is not None:
                total_red_cards += r_cards
        
        # Get last 5 results for form
        recent_form = ''.join(recent_results[-5:]) if recent_results else ""
        
        # Calculate data freshness
        timestamps = [m.data_fetched_at for m in matches if hasattr(m, 'data_fetched_at') and m.data_fetched_at]
        last_updated = max(timestamps) if timestamps else None
        
        return TeamStatistics(
            team_id=team_id or team_name.lower().replace(" ", "_"),
            matches_played=matches_played,
            wins=wins,
            draws=draws,
            losses=losses,
            goals_scored=goals_scored,
            goals_conceded=goals_conceded,
            home_wins=home_wins,
            away_wins=away_wins,
            total_corners=total_corners,
            total_yellow_cards=total_yellow_cards,
            total_red_cards=total_red_cards,
            recent_form=recent_form,
            data_updated_at=last_updated,
        )

    @staticmethod
    def calculate_league_averages(matches: List[Match]) -> 'LeagueAverages':
        """
        Calculate league-wide averages from match history.
        
        Args:
            matches: List of historical matches
            
        Returns:
            LeagueAverages value object with computed averages
        """
        from src.domain.value_objects.value_objects import LeagueAverages
        
        if not matches:
            # Return default averages when no data
            return LeagueAverages(
                avg_home_goals=1.4,
                avg_away_goals=1.1,
                avg_total_goals=2.5,
            )
        
        total_home_goals = 0
        total_away_goals = 0
        matches_with_goals = 0
        
        for match in matches:
            if not match.is_played:
                continue
                
            # Goals
            if match.home_goals is not None and match.away_goals is not None:
                total_home_goals += match.home_goals
                total_away_goals += match.away_goals
                matches_with_goals += 1
        
        # Calculate averages with fallbacks
        avg_home = total_home_goals / matches_with_goals if matches_with_goals > 0 else 1.4
        avg_away = total_away_goals / matches_with_goals if matches_with_goals > 0 else 1.1
        avg_total = avg_home + avg_away
        
        return LeagueAverages(
            avg_home_goals=avg_home,
            avg_away_goals=avg_away,
            avg_total_goals=avg_total,
        )



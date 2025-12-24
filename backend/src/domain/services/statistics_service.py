"""
Statistics Domain Service

Handles calculation of team statistics from match history.
"""

from typing import List, Optional
import unicodedata
from src.domain.entities.entities import Match, TeamStatistics

class StatisticsService:
    """
    STRICT POLICY:
    - NO MOCK DATA ALLOWED.
    - All calculations must be based exclusively on REAL match results.
    - DO NOT invent statistics if history is missing.
    - If no historical data is available, returns zeros/empty objects.
    
    CORE LOGIC PROTECTION RULE:
    - The statistical aggregation logic in this file is verified for production.
    - MODIFICATION OF CORE CALCULATION LOGIC IS FORBIDDEN to preserve data integrity.
    - New metrics must be implemented by EXTENDING the logic, not changing existing formulas.
    """
    @staticmethod
    def _resolve_alias(name: str) -> str:
        """Resolve common team name aliases."""
        aliases = {
            # England (Premier League)
            "man city": "manchester city",
            "mancity": "manchester city",
            "manchester city fc": "manchester city",
            "manchester city": "manchester city",
            "man utd": "manchester united",
            "manutd": "manchester united",
            "man united": "manchester united",
            "manchester united fc": "manchester united",
            "manchester united": "manchester united",
            "spurs": "tottenham",
            "tottenham hotspur fc": "tottenham",
            "tottenham hotspur": "tottenham",
            "tottenham": "tottenham",
            "wolves": "wolverhampton",
            "wolverhampton wanderers fc": "wolverhampton",
            "wolverhampton wanderers": "wolverhampton",
            "wolverhampton": "wolverhampton",
            "nottm forest": "nottingham forest",
            "nottingham forest fc": "nottingham forest",
            "nottingham forest": "nottingham forest",
            "nott'm forest": "nottingham forest",
            "forest": "nottingham forest",
            "sheff utd": "sheffield united",
            "sheffield united": "sheffield united",
            "sheffield utd": "sheffield united",
            "newcastle": "newcastle united",
            "newcastle united fc": "newcastle united",
            "newcastle united": "newcastle united",
            "brighton": "brighton",
            "brighton & hove albion fc": "brighton",
            "brighton & hove albion": "brighton",
            "brighton and hove albion": "brighton",
            "brighton & hove": "brighton",
            "brighton hove albion": "brighton",
            "brighton fc": "brighton",
            "west ham": "west ham united",
            "west ham united fc": "west ham united",
            "west ham united": "west ham united",
            "leicester": "leicester",
            "leicester city": "leicester",
            "leicester city fc": "leicester",
            "leeds": "leeds united",
            "leeds united fc": "leeds united",
            "leeds united": "leeds united",
            "norwich": "norwich",
            "norwich city": "norwich",
            "liverpool fc": "liverpool",
            "liverpool": "liverpool",
            "arsenal fc": "arsenal",
            "arsenal": "arsenal",
            "chelsea fc": "chelsea",
            "chelsea": "chelsea",
            "everton fc": "everton",
            "everton": "everton",
            "fulham fc": "fulham",
            "fulham": "fulham",
            "brentford fc": "brentford",
            "brentford": "brentford",
            "burnley fc": "burnley",
            "burnley": "burnley",
            "sunderland afc": "sunderland",
            "sunderland": "sunderland",
            "afc bournemouth": "bournemouth",
            "bournemouth": "bournemouth",
            "afc bournemouth fc": "bournemouth",
            "crystal palace fc": "crystal palace",
            "crystal palace": "crystal palace",
            "aston villa fc": "aston villa",
            "aston villa": "aston villa",
            "ipswich town fc": "ipswich",
            "ipswich town": "ipswich",
            "ipswich": "ipswich",
            # Spain (La Liga)
            "alaves": "alaves",
            "deportivo alaves": "alaves",
            "ath bilbao": "ath bilbao",
            "athletic club": "ath bilbao",
            "athletic club de bilbao": "ath bilbao",
            "athletic bilbao": "ath bilbao",
            "atletico madrid": "atletico madrid",
            "atletico de madrid": "atletico madrid",
            "atl madrid": "atletico madrid",
            "ath madrid": "atletico madrid",
            "club atletico de madrid": "atletico madrid",
            "barcelona": "barcelona",
            "fc barcelona": "barcelona",
            "betis": "betis",
            "real betis balompié": "betis",
            "real betis": "betis",
            "celta": "celta",
            "rc celta de vigo": "celta",
            "celta vigo": "celta",
            "celta de vigo": "celta",
            "elche": "elche",
            "elche cf": "elche",
            "espanol": "espanol",
            "rcd espanyol de barcelona": "espanol",
            "espanyol": "espanol",
            "getafe": "getafe",
            "getafe cf": "getafe",
            "girona": "girona",
            "girona fc": "girona",
            "levante": "levante",
            "levante ud": "levante",
            "mallorca": "mallorca",
            "rcd mallorca": "mallorca",
            "osasuna": "osasuna",
            "ca osasuna": "osasuna",
            "club atletico osasuna": "osasuna",
            "oviedo": "oviedo",
            "real oviedo": "oviedo",
            "real madrid": "real madrid",
            "real madrid cf": "real madrid",
            "r madrid": "real madrid",
            "sevilla": "sevilla",
            "sevilla fc": "sevilla",
            "sociedad": "sociedad",
            "real sociedad de fútbol": "sociedad",
            "real sociedad": "sociedad",
            "valencia": "valencia",
            "valencia cf": "valencia",
            "vallecano": "vallecano",
            "rayo vallecano de madrid": "vallecano",
            "rayo vallecano": "vallecano",
            "villarreal": "villarreal",
            "villarreal cf": "villarreal",
            # Italy
            "inter": "inter milan",
            "internazionale": "inter milan",
            "milan": "milan",
            "ac milan": "milan",
            # Germany
            "bayern": "bayern munich",
            "bayern munich": "bayern munich",
            "dortmund": "borussia dortmund", 
            "borussia dortmund": "borussia dortmund",
            "leverkusen": "bayer leverkusen",
            "bayer leverkusen": "bayer leverkusen",
            "gladbach": "borussia monchengladbach",
            "borussia monchengladbach": "borussia monchengladbach",
            "frankfurt": "eintracht frankfurt",
            "eintracht frankfurt": "eintracht frankfurt",
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
        
        # 2. Remove accents (Normalize to ASCII approximation)
        nfkd_form = unicodedata.normalize('NFKD', name)
        name = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
        
        # 3. Standard cleanup
        # Remove common prefixes/suffixes
        remove = ["fc", "cf", "as", "sc", "ac", "real", "sporting", "club", "de", "le", "la", "afc"]
        
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
    def _is_team_match(target: str, candidate: str) -> bool:
        """
        Unified logic to check if a candidate team matches the target team.
        Uses both normalized (alias-aware) and raw comparisons.
        """
        if not target or not candidate:
            return False
            
        # 1. Normalize (handles aliases)
        t_norm = StatisticsService._normalize_name(target)
        c_norm = StatisticsService._normalize_name(candidate)
        
        # 2. Raw (fallback)
        t_raw = target.lower().strip()
        c_raw = candidate.lower().strip()
        
        # Exact matches
        if t_norm == c_norm or t_raw == c_raw:
            return True
            
        # Fuzzy matches (Startswith / Contains)
        # Allow short prefix matches (2+ chars) for search-as-you-type
        if len(t_norm) >= 2:
            if c_norm.startswith(t_norm): return True
            if len(t_norm) >= 4 and t_norm in c_norm: return True
            
        if len(t_raw) >= 2:
            if c_raw.startswith(t_raw): return True
            if len(t_raw) >= 4 and t_raw in c_raw: return True
            
        return False

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
        
        # Granular venue stats
        home_matches_played = 0
        home_goals_scored_total = 0
        home_goals_conceded_total = 0
        
        away_matches_played = 0
        away_goals_scored_total = 0
        away_goals_conceded_total = 0
        
        # New stats for picks
        total_corners = 0
        total_yellow_cards = 0
        total_red_cards = 0
        
        recent_results = []
        
        # Normalize target once for strict comparison
        target_norm = StatisticsService._normalize_name(team_name)
        
        for match in matches:
            if not match.is_played:
                continue
            
            # Use STRICT comparison for statistics to ensure data integrity.
            # Fuzzy matching (_is_team_match) is only for search UIs, not for calculating historical stats.
            # This prevents "Real Madrid" stats from being polluted by "Atletico Madrid" or "Inter Milan" by "Milan".
            home_norm = StatisticsService._normalize_name(match.home_team.name)
            away_norm = StatisticsService._normalize_name(match.away_team.name)
            
            is_home = home_norm == target_norm
            is_away = away_norm == target_norm
            
            if not (is_home or is_away):
                continue
            
            if team_id is None:
                team_id = match.home_team.id if is_home else match.away_team.id
            
            matches_played += 1
            if is_home:
                home_matches_played += 1
            else:
                away_matches_played += 1
            
            # Get stats based on role
            goals_for = match.home_goals if is_home else match.away_goals
            goals_against = match.away_goals if is_home else match.home_goals
            
            # Robustly handle None goals
            if goals_for is None or goals_against is None:
                continue
                
            goals_scored += goals_for
            goals_conceded += goals_against
            
            if is_home:
                home_goals_scored_total += goals_for
                home_goals_conceded_total += goals_against
            else:
                away_goals_scored_total += goals_for
                away_goals_conceded_total += goals_against
            
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
            home_matches_played=home_matches_played,
            home_goals_scored=home_goals_scored_total,
            home_goals_conceded=home_goals_conceded_total,
            away_matches_played=away_matches_played,
            away_goals_scored=away_goals_scored_total,
            away_goals_conceded=away_goals_conceded_total,
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
            # STRICT: Return ZEROS when no data. Do not use mock averages.
            return LeagueAverages(
                avg_home_goals=0.0,
                avg_away_goals=0.0,
                avg_total_goals=0.0,
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
        avg_home = total_home_goals / matches_with_goals if matches_with_goals > 0 else 0.0
        avg_away = total_away_goals / matches_with_goals if matches_with_goals > 0 else 0.0
        avg_total = avg_home + avg_away
        
        return LeagueAverages(
            avg_home_goals=avg_home,
            avg_away_goals=avg_away,
            avg_total_goals=avg_total,
        )

"""
Statistics Domain Service

Handles calculation of team statistics from match history.
"""

from typing import List, Optional
import unicodedata
from src.domain.entities.entities import Match, TeamStatistics, TeamH2HStatistics



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
            # France
            "racing club de lens": "lens",
            "rc lens": "lens",
            "psg": "paris sg",
            "paris saint germain": "paris sg",
            "paris saint-germain": "paris sg",
            "st brestois": "brest",
            "stade brestois 29": "brest",
            "stade de reims": "reims",
            "stade rennais fc": "rennes",
            "stade rennais": "rennes",
            "rennais": "rennes",
            "ogc nice": "nice",
            "olympique lyonnais": "lyon",
            "olympique de marseille": "marseille",
            "as monaco": "monaco",
            "lille osc": "lille",
            "montpellier hsc": "montpellier",
            "clermont foot": "clermont",
            "clermont foot 63": "clermont",
            "fc nantes": "nantes",
            "toulouse fc": "toulouse",
            "le havre ac": "le havre",
            "fc metz": "metz",
            "fc lorient": "lorient",
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

    _normalization_cache = {}

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize team name for comparison. Cached for performance."""
        if name in StatisticsService._normalization_cache:
            return StatisticsService._normalization_cache[name]
            
        # 1. Resolve Aliases first
        original_name = name
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
                
        result = cleaned.strip().replace(" ", "")
        StatisticsService._normalization_cache[original_name] = result
        return result

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
        matches_with_corners = 0
        matches_with_cards = 0
        
        # Extended Stats
        total_shots = 0
        total_shots_on_target = 0
        total_fouls = 0
        matches_with_shots = 0
        matches_with_fouls = 0
        
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
                matches_with_corners += 1
                
            # Accumulate cards
            y_cards = match.home_yellow_cards if is_home else match.away_yellow_cards
            r_cards = match.home_red_cards if is_home else match.away_red_cards
            
            if y_cards is not None:
                total_yellow_cards += y_cards
                matches_with_cards += 1
            if r_cards is not None:
                total_red_cards += r_cards

            # Accumulate Extended Stats (Shots, Fouls)
            shots = match.home_total_shots if is_home else match.away_total_shots
            sot = match.home_shots_on_target if is_home else match.away_shots_on_target
            
            if shots is not None:
                total_shots += shots
                matches_with_shots += 1
            if sot is not None:
                total_shots_on_target += sot
                # matches_with_shots counter handles both usually, but let's assume they come together
            
            fouls = match.home_fouls if is_home else match.away_fouls
            if fouls is not None:
                total_fouls += fouls
                matches_with_fouls += 1
        
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
            matches_with_corners=matches_with_corners,
            matches_with_cards=matches_with_cards,
            recent_form=recent_form,
            data_updated_at=last_updated,
            total_shots=total_shots,
            total_shots_on_target=total_shots_on_target,
            total_fouls=total_fouls,
            matches_with_shots=matches_with_shots,
            matches_with_fouls=matches_with_fouls,
        )

    @staticmethod
    def create_empty_stats_dict() -> dict:
        """Create a dictionary for tracking stats incrementally."""
        return {
            "matches_played": 0, "wins": 0, "draws": 0, "losses": 0,
            "goals_scored": 0, "goals_conceded": 0,
            "corners_for": 0, "corners_against": 0,
            "yellow_cards": 0, "red_cards": 0,
            "home_wins": 0, "away_wins": 0,
            "matches_with_corners": 0,
            "matches_with_cards": 0,
            "shots": 0, "shots_on_target": 0, "fouls": 0,
            "matches_with_shots": 0, "matches_with_fouls": 0,
        }

    @staticmethod
    def update_team_stats_dict(stats: dict, match: Match, is_home: bool):
        """Update a stats dictionary with a new match result."""
        goals_for = match.home_goals if is_home else match.away_goals
        goals_against = match.away_goals if is_home else match.home_goals
        
        if goals_for is None or goals_against is None:
            return

        stats["matches_played"] += 1
        stats["goals_scored"] += goals_for
        stats["goals_conceded"] += goals_against
        
        if goals_for > goals_against:
            stats["wins"] += 1
            if is_home: stats["home_wins"] += 1
            else: stats["away_wins"] += 1
        elif goals_for == goals_against:
            stats["draws"] += 1
        else:
            stats["losses"] += 1
            
        if match.home_corners is not None and match.away_corners is not None:
            stats["corners_for"] += match.home_corners if is_home else match.away_corners
            stats["corners_against"] += match.away_corners if is_home else match.home_corners
            stats["matches_with_corners"] += 1
            
        if match.home_yellow_cards is not None:
            stats["yellow_cards"] += match.home_yellow_cards if is_home else match.away_yellow_cards
            stats["matches_with_cards"] += 1
            
        if match.home_red_cards is not None:
            stats["red_cards"] += match.home_red_cards if is_home else match.away_red_cards

        # Extended Stats
        shots = match.home_total_shots if is_home else match.away_total_shots
        sot = match.home_shots_on_target if is_home else match.away_shots_on_target
        fouls = match.home_fouls if is_home else match.away_fouls
        
        if shots is not None:
            stats["shots"] += shots
            stats["matches_with_shots"] += 1
        if sot is not None:
            stats["shots_on_target"] += sot
            
        if fouls is not None:
            stats["fouls"] += fouls
            stats["matches_with_fouls"] += 1

    @staticmethod
    def convert_to_domain_stats(team_name: str, raw_stats: dict) -> TeamStatistics:
        """Convert a raw stats dictionary to a TeamStatistics domain entity."""
        mp = raw_stats["matches_played"]
        return TeamStatistics(
            team_id=team_name.lower().replace(" ", "_"),
            matches_played=mp,
            wins=raw_stats.get("wins", 0),
            draws=raw_stats.get("draws", 0),
            losses=raw_stats.get("losses", 0),
            goals_scored=raw_stats["goals_scored"],
            goals_conceded=raw_stats["goals_conceded"],
            home_wins=raw_stats.get("home_wins", 0),
            away_wins=raw_stats.get("away_wins", 0),
            total_corners=raw_stats.get("corners_for", 0),
            total_yellow_cards=raw_stats.get("yellow_cards", 0),
            total_red_cards=raw_stats.get("red_cards", 0),
            matches_with_corners=raw_stats.get("matches_with_corners", 0),
            matches_with_cards=raw_stats.get("matches_with_cards", 0),
            total_shots=raw_stats.get("shots", 0),
            total_shots_on_target=raw_stats.get("shots_on_target", 0),
            total_fouls=raw_stats.get("fouls", 0),
            matches_with_shots=raw_stats.get("matches_with_shots", 0),
            matches_with_fouls=raw_stats.get("matches_with_fouls", 0),
            recent_form="" # Form is calculated from full history if needed
        )

    def calculate_league_averages(self, matches: List[Match]) -> 'LeagueAverages':
        """
        Calculate league-wide averages from match history.
        
        Args:
            matches: List of historical matches
            
        Returns:
            LeagueAverages value object with computed averages
        """
        
        total_home_goals = 0
        total_away_goals = 0
        total_corners = 0
        total_cards = 0
        matches_with_goals = 0
        matches_with_corners = 0
        matches_with_cards = 0
        
        for match in matches:
            if not match.is_played:
                continue
                
            if match.home_goals is not None and match.away_goals is not None:
                total_home_goals += match.home_goals
                total_away_goals += match.away_goals
                matches_with_goals += 1

            if match.home_corners is not None and match.away_corners is not None:
                total_corners += (match.home_corners + match.away_corners)
                matches_with_corners += 1

            if match.home_yellow_cards is not None and match.away_yellow_cards is not None:
                total_cards += (match.home_yellow_cards + match.away_yellow_cards)
                matches_with_cards += 1
        
        # Calculate averages with fallbacks
        from src.domain.value_objects.value_objects import LeagueAverages

        if matches_with_goals == 0:
            return None
            
        return LeagueAverages(
            avg_home_goals=total_home_goals / matches_with_goals,
            avg_away_goals=total_away_goals / matches_with_goals,
            avg_total_goals=(total_home_goals + total_away_goals) / matches_with_goals,
            avg_corners=total_corners / matches_with_corners if matches_with_corners > 0 else 9.5,
            avg_cards=total_cards / matches_with_cards if matches_with_cards > 0 else 4.5
        )

    @staticmethod
    def calculate_h2h_statistics(
        team_a_name: str,
        team_b_name: str,
        matches: List[Match],
    ) -> TeamH2HStatistics:
        """
        Calculate H2H statistics between two teams.
        
        Args:
            team_a_name: Name of team A
            team_b_name: Name of team B
            matches: List of historical matches to search
            
        Returns:
            TeamH2HStatistics object
        """
        matches_played = 0
        team_a_wins = 0
        team_b_wins = 0
        draws = 0
        team_a_goals = 0
        team_b_goals = 0
        recent_matches = []
        
        team_a_norm = StatisticsService._normalize_name(team_a_name)
        team_b_norm = StatisticsService._normalize_name(team_b_name)
        
        # Sort matches by date descending (newest first)
        sorted_matches = sorted(matches, key=lambda x: x.match_date, reverse=True)
        
        for match in sorted_matches:
            if not match.is_played:
                continue
                
            home_norm = StatisticsService._normalize_name(match.home_team.name)
            away_norm = StatisticsService._normalize_name(match.away_team.name)
            
            # Check if this match involves both teams
            is_a_home = home_norm == team_a_norm
            is_a_away = away_norm == team_a_norm
            is_b_home = home_norm == team_b_norm
            is_b_away = away_norm == team_b_norm
            
            match_found = False
            a_score = 0
            b_score = 0
            
            if is_a_home and is_b_away:
                match_found = True
                a_score = match.home_goals or 0
                b_score = match.away_goals or 0
                date_str = match.match_date.strftime("%Y-%m-%d")
                recent_matches.append({
                    "date": date_str,
                    "home": match.home_team.name,
                    "away": match.away_team.name,
                    "score": f"{a_score}-{b_score}",
                    "winner": "A" if a_score > b_score else "B" if b_score > a_score else "Draw"
                })
            elif is_b_home and is_a_away:
                match_found = True
                b_score = match.home_goals or 0
                a_score = match.away_goals or 0
                date_str = match.match_date.strftime("%Y-%m-%d")
                recent_matches.append({
                    "date": date_str,
                    "home": match.home_team.name,
                    "away": match.away_team.name,
                    "score": f"{b_score}-{a_score}",
                    "winner": "B" if b_score > a_score else "A" if a_score > b_score else "Draw"
                })
                
            if match_found:
                matches_played += 1
                team_a_goals += a_score
                team_b_goals += b_score
                
                if a_score > b_score:
                    team_a_wins += 1
                elif b_score > a_score:
                    team_b_wins += 1
                else:
                    draws += 1
        
        return TeamH2HStatistics(
            team_a_id=team_a_name,
            team_b_id=team_b_name,
            matches_played=matches_played,
            team_a_wins=team_a_wins,
            draws=draws,
            team_b_wins=team_b_wins,
            team_a_goals=team_a_goals,
            team_b_goals=team_b_goals,
            recent_matches=recent_matches
        )

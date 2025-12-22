"""
Context Analyzer Service Module

Analyzes the context of a match using available statistical data
to provide weighting factors for prediction models.
"""

from src.domain.entities.entities import Match, TeamStatistics

class ContextAnalyzer:
    """
    Analyzes match context to provide dynamic weighting factors.
    
    Factors considered:
    - Home Advantage Strength (based on team history)
    - Form Momentum (recent performance trend)
    - Importance (basic heuristics)
    """
    
    def analyze_match_context(
        self,
        match: Match,
        home_stats: TeamStatistics,
        away_stats: TeamStatistics
    ) -> dict:
        """
        Analyze the full context of a match.
        
        Args:
            match: The match entity
            home_stats: Home team statistics
            away_stats: Away team statistics
            
        Returns:
            Dictionary with context factors
        """
        return {
            'home_advantage_strength': self._calculate_home_advantage(home_stats),
            'form_momentum_home': self._calculate_momentum(home_stats),
            'form_momentum_away': self._calculate_momentum(away_stats),
            'importance': self._calculate_importance(match),
            # 'rivalry': Not implemented (requires h2h database)
            # 'weather': Not implemented (requires external API)
        }
    
    def _calculate_home_advantage(self, stats: TeamStatistics) -> float:
        """
        Calculate how much better the team performs at home vs away.
        Returns a factor > 1.0 if strong home advantage.
        """
        if not stats or stats.matches_played < 5:
            return 1.10  # Standard default
            
        # Avoid division by zero
        total_games = stats.matches_played
        home_games = total_games / 2  # Approximation if split unknown
        
        # Calculate win rates
        global_win_rate = stats.wins / total_games
        home_win_rate = stats.home_wins / (home_games + 0.1) # smooth
        
        if global_win_rate == 0:
            return 1.10
            
        advantage = home_win_rate / global_win_rate
        
        # Cap to realistic values (0.8 - 1.5)
        return max(0.8, min(1.5, advantage))

    def _calculate_momentum(self, stats: TeamStatistics) -> float:
        """
        Calculate form momentum from recent results.
        Returns 0.0 (terrible) to 1.0 (perfect).
        """
        if not stats or not stats.recent_form:
            return 0.5
            
        # Recent form string: e.g. "WWDLW" (newest last)
        form = stats.recent_form
        if not form:
            return 0.5
            
        # Weights for last 5 matches (newest has higher weight)
        weights = [0.1, 0.15, 0.2, 0.25, 0.3]
        
        score = 0.0
        total_weight = 0.0
        
        # Pad form if less than 5
        padded_form = form.rjust(5, 'D')[-5:]
        
        for i, result in enumerate(padded_form):
            val = 0.5 # Draw
            if result == 'W':
                val = 1.0
            elif result == 'L':
                val = 0.0
                
            score += val * weights[i]
            total_weight += weights[i]
            
        return score / total_weight

    def _calculate_importance(self, match: Match) -> float:
        """
        Estimate match importance.
        Current heuristic: Default to 1.0 as we lack calendar context.
        """
        # Future improvement: Check if it's a cup final, relegation battle, etc.
        return 1.0

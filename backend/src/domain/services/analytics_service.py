"""
Analytics Domain Service

Handles calculation of bot performance statistics and pick efficiency.
"""

from typing import List, Dict, Any
from collections import defaultdict

class AnalyticsService:
    """
    Service responsible for aggregating prediction results to measure bot performance.
    """
    
    @staticmethod
    def calculate_pick_efficiency(predictions: List[Any]) -> List[Dict[str, Any]]:
        """
        Calculates the efficiency of different pick types based on prediction history.
        
        Args:
            predictions: List of Prediction entities. 
                        Expected to have 'pick_type' (str) and 'status' (str) attributes.
                        Status values expected: 'WON', 'LOST', 'VOID', 'PENDING'.
                        
        Returns:
            List of dictionaries containing stats per pick type, sorted by efficiency.
        """
        # Dictionary to store stats: {pick_type: {won: 0, lost: 0, ...}}
        stats = defaultdict(lambda: {"won": 0, "lost": 0, "void": 0, "total": 0})
        
        for pred in predictions:
            # Ensure we have necessary attributes
            if not hasattr(pred, 'status') or not pred.status:
                continue
                
            status = pred.status.upper()
            
            # Skip pending predictions as they don't contribute to historical efficiency
            if status == 'PENDING':
                continue
                
            # Normalize pick type (handle None or empty)
            pick_type = getattr(pred, 'pick_type', 'Unknown') or 'Unknown'
            
            stats[pick_type]["total"] += 1
            
            if status == 'WON':
                stats[pick_type]["won"] += 1
            elif status == 'LOST':
                stats[pick_type]["lost"] += 1
            elif status == 'VOID':
                stats[pick_type]["void"] += 1
        
        # Transform to list and calculate percentages
        result = []
        for p_type, data in stats.items():
            # Efficiency = Won / (Won + Lost). Void bets are usually excluded from ROI/Strike Rate calc.
            decisive_bets = data["won"] + data["lost"]
            efficiency = (data["won"] / decisive_bets * 100) if decisive_bets > 0 else 0.0
            
            result.append({
                "pick_type": p_type,
                "won": data["won"],
                "lost": data["lost"],
                "void": data["void"],
                "total": data["total"],
                "efficiency": round(efficiency, 2)
            })
            
        # Sort by efficiency descending (best performing picks first)
        return sorted(result, key=lambda x: x["efficiency"], reverse=True)
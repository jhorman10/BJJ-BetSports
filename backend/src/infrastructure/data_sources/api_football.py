"""
API-Football Data Source (LEGACY/MAPPING ONLY)

This file is maintained for backward compatibility and mapping purposes.
The main data source has migrated to Football-Data.org, but internal mappings
to API-Football IDs are still used by some services.
"""

import logging

logger = logging.getLogger(__name__)

# Mapping of our internal league codes to API-Football competition IDs
# This is used for cross-referencing and historical data consistency.
LEAGUE_ID_MAPPING = {
    "E0": 39,   # Premier League
    "E1": 40,   # Championship
    "E2": 41,   # League One
    "E_FA": 45, # FA Cup
    "SP1": 140, # La Liga
    "SP2": 141, # Segunda División
    "SP_C": 143, # Copa del Rey
    "D1": 78,   # Bundesliga
    "D2": 79,   # 2. Bundesliga
    "I1": 135,  # Serie A
    "I2": 136,  # Serie B
    "F1": 61,   # Ligue 1
    "F2": 62,   # Ligue 2
    "N1": 88,   # Eredivisie
    "N2": 89,   # Eerste Divisie (Netherlands 2)
    "B1": 144,  # Jupiler Pro League
    "B2": 145,  # Challenger Pro League (Belgium 2)
    "P1": 94,   # Primeira Liga
    "P2": 95,   # Liga Portugal 2
}

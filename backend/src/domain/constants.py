"""
Domain Constants

This module contains constant definitions valid across the domain layer.
"""

ORDERED_INTERNATIONAL_TOURNAMENTS = (
    "UCL",
    "UEL",
    "UECL",
    "EURO",
    "WC",
    "LIB",
    "SUD",
)

CLUB_INTERNATIONAL_LEAGUES = frozenset({"UCL", "UEL", "UECL", "LIB", "SUD"})
NATIONAL_TEAM_TOURNAMENTS = frozenset({"EURO", "WC"})
ALL_INTERNATIONAL_TOURNAMENTS = CLUB_INTERNATIONAL_LEAGUES | NATIONAL_TEAM_TOURNAMENTS

# Mapping of league codes to metadata
LEAGUES_METADATA = {
    # England
    "E0": {"name": "Premier League", "country": "England"},
    "E1": {"name": "Championship", "country": "England"},
    "E_FA": {"name": "FA Cup", "country": "England"},
    "E2": {"name": "League One", "country": "England"},
    "E3": {"name": "League Two", "country": "England"},
    # Spain
    "SP1": {"name": "La Liga", "country": "Spain"},
    "SP2": {"name": "Segunda División", "country": "Spain"},
    "SP_C": {"name": "Copa del Rey", "country": "Spain"},
    # Germany
    "D1": {"name": "Bundesliga", "country": "Germany"},
    "D2": {"name": "2. Bundesliga", "country": "Germany"},
    # Italy
    "I1": {"name": "Serie A", "country": "Italy"},
    "I2": {"name": "Serie B", "country": "Italy"},
    # France
    "F1": {"name": "Ligue 1", "country": "France"},
    "F2": {"name": "Ligue 2", "country": "France"},
    # Netherlands
    "N1": {"name": "Eredivisie", "country": "Netherlands"},
    "N2": {"name": "Eerste Divisie", "country": "Netherlands"},
    # Belgium
    "B1": {"name": "Jupiler Pro League", "country": "Belgium"},
    "B2": {"name": "Challenger Pro League", "country": "Belgium"},
    # Portugal
    "P1": {"name": "Primeira Liga", "country": "Portugal"},
    "P2": {"name": "Liga Portugal 2", "country": "Portugal"},
    # International (Europe & Americas)
    "UCL": {"name": "Champions League", "country": "International"},
    "UEL": {"name": "Europa League", "country": "International"},
    "UECL": {"name": "Conference League", "country": "International"},
    "EURO": {"name": "Euro Championship", "country": "International"},
    "LIB": {"name": "Copa Libertadores", "country": "International"},
    "SUD": {"name": "Copa Sudamericana", "country": "International"},
    "WC": {"name": "World Cup", "country": "International"},
    # South America
    "COL1": {"name": "Liga BetPlay", "country": "Colombia"},
    "ARG1": {"name": "Liga Profesional", "country": "Argentina"},
    "BRA1": {"name": "Série A", "country": "Brazil"},
}

# Default set of league codes considered for predictions
DEFAULT_LEAGUES = list(LEAGUES_METADATA.keys())

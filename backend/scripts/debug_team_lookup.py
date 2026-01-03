import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "../"))
from src.domain.services.team_service import TeamService
from src.domain.services.statistics_service import StatisticsService

def test_team(name):
    print(f"--- Testing: '{name}' ---")
    normalized = StatisticsService._normalize_name(name)
    print(f"Normalized: '{normalized}'")
    logo = TeamService.get_team_logo(name)
    short = TeamService.get_team_short_name(name)
    print(f"Short Name: '{short}'")
    print(f"Logo Found: {'YES' if logo else 'NO'}")
    if logo:
        print(f"URL: {logo}")
    else:
        print("!! MISSING LOGO !!")

teams_to_check = [
    "Paris Saint-Germain",
    "Paris Saint Germain",
    "PSG",
    "Paris SG",
    "Olympique de Marseille",
    "Marseille",
    "Olympique Lyonnais",
    "Lyon",
    "OL",
    "AS Monaco",
    "Monaco",
    "Lille OSC",
    "LOSC",
    "Stade Rennais",
    "Rennes",
    "Borussia Dortmund",
    "Bayer Leverkusen",
    "Inter Milan",
    "Internazionale",
    "AC Milan",
    "Milan",
    "Royale Union Saint-Gilloise",
    "Union Saint-Gilloise",
    "Union SG",
    "RUSG",
    "KAA Gent",
    "Gent",
    "RSC Anderlecht",
    "Anderlecht",
    "Club Brugge KV",
    "Club Brugge",
    "KV Mechelen",
    "Atletico Madrid",
    "Atletico de Madrid",
    "Real Betis",
    "Real Sociedad",
    "Rayo Vallecano",
    "Sporting CP",
    "Sporting Lisbon",
    "Benfica",
    "FC Porto",
    "SC Braga",
    "Braga",
    "Vitoria Guimaraes"
]

TeamService.load_logos()
print(f"Total logos loaded: {len(TeamService._logos)}")

for t in teams_to_check:
    test_team(t)

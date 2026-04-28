"""Resolve competition context for clubs and national teams."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Sequence

from src.domain.constants import ALL_INTERNATIONAL_TOURNAMENTS, NATIONAL_TEAM_TOURNAMENTS
from src.domain.entities.entities import Match
from src.domain.services.statistics_service import StatisticsService

ParticipantType = Literal["club", "national_team"]


@dataclass(frozen=True)
class TeamCompetitionContext:
    participant_type: ParticipantType
    base_competition_id: str | None
    support_competition_ids: tuple[str, ...]
    confidence: float
    evidence: dict[str, Any]


class TeamCompetitionContextResolver:
    """Infer the best competition context available for a participant."""

    def __init__(self, domestic_window_days: int = 540) -> None:
        self.domestic_window_days = domestic_window_days

    def resolve(
        self,
        team_name: str,
        target_match: Match,
        candidate_matches: Sequence[Match],
    ) -> TeamCompetitionContext:
        normalized_team_name = StatisticsService.normalize_team_name(team_name)
        relevant_matches = self._collect_team_matches(
            normalized_team_name, candidate_matches
        )

        if target_match.league.id in NATIONAL_TEAM_TOURNAMENTS:
            return self._resolve_national_team_context(
                normalized_team_name, target_match, relevant_matches
            )

        return self._resolve_club_context(
            normalized_team_name, target_match, relevant_matches
        )

    def _resolve_club_context(
        self,
        normalized_team_name: str,
        target_match: Match,
        relevant_matches: Sequence[Match],
    ) -> TeamCompetitionContext:
        domestic_matches = [
            match
            for match in relevant_matches
            if match.league.id not in ALL_INTERNATIONAL_TOURNAMENTS
        ]
        international_matches = [
            match
            for match in relevant_matches
            if match.league.id in ALL_INTERNATIONAL_TOURNAMENTS
        ]

        if not domestic_matches:
            support_competition_ids = tuple(
                sorted({match.league.id for match in relevant_matches})
            )
            return TeamCompetitionContext(
                participant_type="club",
                base_competition_id=None,
                support_competition_ids=support_competition_ids,
                confidence=0.35 if support_competition_ids else 0.0,
                evidence={
                    "normalized_team_name": normalized_team_name,
                    "target_league_id": target_match.league.id,
                    "relevant_match_count": len(relevant_matches),
                    "domestic_match_count": 0,
                    "international_match_count": len(international_matches),
                    "resolution": "no_domestic_context",
                },
            )

        target_season_key = self._season_key(target_match)
        competition_scores: dict[str, float] = {}
        competition_match_counts: dict[str, int] = {}

        for match in domestic_matches:
            league_id = match.league.id
            days_gap = abs((target_match.match_date - match.match_date).days)
            recency_weight = max(
                0.0,
                1.0 - min(days_gap, self.domestic_window_days) / self.domestic_window_days,
            )
            season_bonus = 0.75 if self._season_key(match) == target_season_key else 0.0
            score = 1.0 + recency_weight + season_bonus
            competition_scores[league_id] = competition_scores.get(league_id, 0.0) + score
            competition_match_counts[league_id] = competition_match_counts.get(league_id, 0) + 1

        ranked_competitions = sorted(
            competition_scores.items(),
            key=lambda item: (
                -item[1],
                -competition_match_counts[item[0]],
                item[0],
            ),
        )
        base_competition_id, top_score = ranked_competitions[0]
        second_score = ranked_competitions[1][1] if len(ranked_competitions) > 1 else 0.0
        total_score = sum(competition_scores.values())
        top_share = top_score / total_score if total_score else 1.0
        confidence = min(
            0.99,
            0.45 + (top_share * 0.35) + (min(max(top_score - second_score, 0.0), 3.0) * 0.08),
        )

        support_competition_ids = tuple(
            sorted(
                {
                    match.league.id
                    for match in relevant_matches
                    if match.league.id != base_competition_id
                }
            )
        )

        evidence: dict[str, Any] = {
            "normalized_team_name": normalized_team_name,
            "target_league_id": target_match.league.id,
            "relevant_match_count": len(relevant_matches),
            "domestic_match_count": len(domestic_matches),
            "international_match_count": len(international_matches),
            "competition_scores": {
                league_id: round(score, 4)
                for league_id, score in competition_scores.items()
            },
            "dominant_match_count": competition_match_counts[base_competition_id],
        }
        if len(ranked_competitions) > 1:
            evidence["runner_up_competition_id"] = ranked_competitions[1][0]
            evidence["runner_up_score"] = round(ranked_competitions[1][1], 4)

        return TeamCompetitionContext(
            participant_type="club",
            base_competition_id=base_competition_id,
            support_competition_ids=support_competition_ids,
            confidence=round(confidence, 4),
            evidence=evidence,
        )

    def _resolve_national_team_context(
        self,
        normalized_team_name: str,
        target_match: Match,
        relevant_matches: Sequence[Match],
    ) -> TeamCompetitionContext:
        national_context_matches = [
            match
            for match in relevant_matches
            if match.league.id in NATIONAL_TEAM_TOURNAMENTS
        ]
        excluded_club_competitions = sorted(
            {
                match.league.id
                for match in relevant_matches
                if match.league.id not in NATIONAL_TEAM_TOURNAMENTS
            }
        )
        support_competition_ids = tuple(
            sorted(
                {
                    match.league.id
                    for match in national_context_matches
                    if match.league.id != target_match.league.id
                }
            )
        )
        confidence = 0.9 if national_context_matches else 0.6

        return TeamCompetitionContext(
            participant_type="national_team",
            base_competition_id=target_match.league.id,
            support_competition_ids=support_competition_ids,
            confidence=confidence,
            evidence={
                "normalized_team_name": normalized_team_name,
                "target_league_id": target_match.league.id,
                "relevant_match_count": len(relevant_matches),
                "national_context_match_count": len(national_context_matches),
                "excluded_club_competitions": excluded_club_competitions,
            },
        )

    @staticmethod
    def _collect_team_matches(
        normalized_team_name: str, candidate_matches: Sequence[Match]
    ) -> list[Match]:
        return [
            match
            for match in candidate_matches
            if TeamCompetitionContextResolver._match_contains_team(
                normalized_team_name, match
            )
        ]

    @staticmethod
    def _match_contains_team(normalized_team_name: str, match: Match) -> bool:
        home_team_name = StatisticsService.normalize_team_name(match.home_team.name)
        away_team_name = StatisticsService.normalize_team_name(match.away_team.name)
        return normalized_team_name in {home_team_name, away_team_name}

    @staticmethod
    def _season_key(match: Match) -> str:
        if match.league.season:
            return match.league.season

        year = match.match_date.year
        if match.match_date.month >= 7:
            return f"{year}-{year + 1}"
        return f"{year - 1}-{year}"

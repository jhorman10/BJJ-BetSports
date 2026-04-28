from typing import Any


def _process_single_match_task(
    match: Any,
    raw_home: Any,
    raw_away: Any,
    league_averages: Any,
    global_averages_obj: Any,
    prediction_service: Any,
    picks_service: Any,
    statistics_service: Any,
    resolution_service: Any,
    feature_extractor: Any,
) -> tuple[Any, Any, Any, Any, Any] | None:
    """
    Standalone function to process a single match for prediction and pick generation.
    Designed to be picklable for parallel execution.
    """
    try:
        home_stats = statistics_service.convert_to_domain_stats(
            match.home_team.name, raw_home
        )
        away_stats = statistics_service.convert_to_domain_stats(
            match.away_team.name, raw_away
        )

        # PREDICT
        prediction = prediction_service.generate_prediction(
            match=match,
            home_stats=home_stats,
            away_stats=away_stats,
            league_averages=league_averages,
            global_averages=global_averages_obj,
            min_matches=0,
        )

        # GENERATE PICKS
        suggested_picks_container = picks_service.generate_suggested_picks(
            match=match,
            home_stats=home_stats,
            away_stats=away_stats,
            league_averages=league_averages,
            predicted_home_goals=prediction.predicted_home_goals,
            predicted_away_goals=prediction.predicted_away_goals,
            home_win_prob=prediction.home_win_probability,
            draw_prob=prediction.draw_probability,
            away_win_prob=prediction.away_win_probability,
        )

        return (
            match,
            prediction,
            suggested_picks_container,
            home_stats,
            away_stats,
        )

    except Exception:
        # We can't log easily here if pickling logger issues arise, so just return None
        return None

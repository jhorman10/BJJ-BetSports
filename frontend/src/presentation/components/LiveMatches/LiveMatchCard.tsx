import React, { memo } from "react";
import { Box, Typography, Card, CardContent, Stack, Chip } from "@mui/material";
import { AccessTime } from "@mui/icons-material";

import { LiveMatch } from "../../../hooks/useLiveMatches";
import { LiveMatchPrediction } from "../../../types";
import { translateMatchStatus } from "../../../utils/translationUtils";
import { getTeamLogo, getTeamDisplayName } from "../../../utils/teamUtils";

import { normalizeMatch } from "./liveMatchUtils";
import { PredictionSection } from "./PredictionSection";

interface MatchCardProps {
  matchData: LiveMatchPrediction | LiveMatch;
}

const isLiveMatchPrediction = (
  data: LiveMatchPrediction | LiveMatch
): data is LiveMatchPrediction => "match" in data;

const LiveMatchCard: React.FC<MatchCardProps> = memo(({ matchData }) => {
  const rawMatch = isLiveMatchPrediction(matchData) ? matchData.match : matchData;
  const prediction = isLiveMatchPrediction(matchData) ? matchData.prediction : undefined;
  const match = normalizeMatch(rawMatch as LiveMatch | import("../../../types").Match);

  const getRecommendation = (): { label: string; value: number } | null => {
    if (!prediction || prediction.confidence === 0) return null;
    const probs = [
      { label: "1", value: validPrediction!.home_win_probability },
      { label: "X", value: validPrediction!.draw_probability },
      { label: "2", value: validPrediction!.away_win_probability },
    ];
    return probs.reduce((a, b) => (a.value > b.value ? a : b));
  };

  const recommendation = getRecommendation();
  const confidence = prediction?.confidence ?? 0;
  const hasValidPrediction = confidence > 0 && prediction !== undefined;
  const validPrediction = hasValidPrediction ? prediction! : null;
  const displayStatus = translateMatchStatus(match.status) || "EN VIVO";

  return (
    <Card
      sx={{
        background: "rgba(30, 41, 59, 0.5)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(239, 68, 68, 0.25)",
        borderRadius: 2,
        position: "relative",
        overflow: "hidden",
        transition: "all 0.3s ease",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: "0 8px 25px rgba(239, 68, 68, 0.15)",
          border: "1px solid rgba(239, 68, 68, 0.4)",
        },
        "&::before": {
          content: '""',
          position: "absolute",
          top: 8,
          left: 8,
          width: 8,
          height: 8,
          borderRadius: "50%",
          backgroundColor: "#ef4444",
          animation: "pulse 2s infinite",
        },
        "@keyframes pulse": {
          "0%": { opacity: 1, transform: "scale(1)" },
          "50%": { opacity: 0.5, transform: "scale(1.2)" },
          "100%": { opacity: 1, transform: "scale(1)" },
        },
      }}
    >
      <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
        <Stack spacing={1.5}>
          {/* Header: Status and League */}
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Chip
              icon={<AccessTime sx={{ fontSize: 14 }} />}
              label={displayStatus}
              size="small"
              color="error"
              sx={{ height: 22, fontSize: "0.7rem", fontWeight: 600, ml: 2 }}
            />
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ maxWidth: 120, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
            >
              {match.leagueName}
            </Typography>
          </Box>

          {/* Teams and Score */}
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Box flex={1} display="flex" flexDirection="column" alignItems="center" sx={{ minWidth: 0 }}>
              {"homeTeam" in match ? (
                <Box
                  component="img"
                  src={getTeamLogo(match.homeTeam)}
                  alt={getTeamDisplayName(match.homeTeam)}
                  sx={{ width: 32, height: 32, mb: 0.5, objectFit: "contain" }}
                />
              ) : null}
              <Typography
                variant="body2"
                fontWeight={500}
                sx={{ width: "100%", textAlign: "center", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
              >
                {match.homeTeamName}
              </Typography>
            </Box>
            <Box
              sx={{
                mx: 1,
                px: 1.5,
                py: 0.5,
                bgcolor: "rgba(0, 0, 0, 0.4)",
                borderRadius: 1.5,
                minWidth: 60,
                textAlign: "center",
              }}
            >
              <Typography variant="h6" fontWeight="bold" color="primary.light">
                {match.homeScore} - {match.awayScore}
              </Typography>
            </Box>
            <Box flex={1} display="flex" flexDirection="column" alignItems="center" sx={{ minWidth: 0 }}>
              {"awayTeam" in match ? (
                <Box
                  component="img"
                  src={getTeamLogo(match.awayTeam)}
                  alt={getTeamDisplayName(match.awayTeam)}
                  sx={{ width: 32, height: 32, mb: 0.5, objectFit: "contain" }}
                />
              ) : null}
              <Typography
                variant="body2"
                fontWeight={500}
                sx={{ width: "100%", textAlign: "center", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
              >
                {match.awayTeamName}
              </Typography>
            </Box>
          </Box>

          {/* Prediction Section */}
          {hasValidPrediction ? (
            <PredictionSection
              validPrediction={validPrediction!}
              confidence={confidence}
              recommendation={recommendation}
            />
          ) : (
            <Box textAlign="center" py={1}>
              <Typography variant="caption" color="text.disabled">
                Sin datos suficientes para predicción
              </Typography>
            </Box>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
});

LiveMatchCard.displayName = "LiveMatchCard";

export default LiveMatchCard;

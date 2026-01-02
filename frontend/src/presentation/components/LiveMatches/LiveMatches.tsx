import React from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  CircularProgress,
  Stack,
  Chip,
  LinearProgress,
  Skeleton,
  Tooltip,
  IconButton,
  Fade,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import {
  LiveTv,
  Refresh,
  SportsScore,
  TrendingUp,
  AccessTime,
} from "@mui/icons-material";
import { useLiveMatches, LiveMatch } from "../../../hooks/useLiveMatches";
import { LiveMatchPrediction } from "../../../types";
import { translateMatchStatus } from "../../../utils/translationUtils";

/**
 * Skeleton component for loading state
 */
const MatchCardSkeleton: React.FC = () => (
  <Card
    sx={{
      background: "rgba(30, 41, 59, 0.4)",
      backdropFilter: "blur(5px)",
      border: "1px solid rgba(148, 163, 184, 0.1)",
      borderRadius: 2,
    }}
  >
    <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
      <Stack spacing={1.5}>
        <Box display="flex" justifyContent="space-between">
          <Skeleton variant="text" width={60} height={20} />
          <Skeleton variant="text" width={80} height={20} />
        </Box>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Skeleton variant="text" width={100} height={24} />
          <Skeleton
            variant="rectangular"
            width={60}
            height={30}
            sx={{ borderRadius: 1 }}
          />
          <Skeleton variant="text" width={100} height={24} />
        </Box>
        <Skeleton
          variant="rectangular"
          width="100%"
          height={8}
          sx={{ borderRadius: 1 }}
        />
      </Stack>
    </CardContent>
  </Card>
);

/**
 * Single live match card with prediction
 */
interface MatchCardProps {
  matchData: LiveMatchPrediction | LiveMatch;
}

// Type guard to check if matchData is a LiveMatchPrediction
const isLiveMatchPrediction = (
  data: LiveMatchPrediction | LiveMatch
): data is LiveMatchPrediction => "match" in data;

// Normalized match data for uniform access
interface NormalizedMatch {
  status: string;
  leagueName: string;
  homeTeamName: string;
  awayTeamName: string;
  homeScore: number;
  awayScore: number;
}

// Normalize match data from either Match or LiveMatch
const normalizeMatch = (
  match: LiveMatch | import("../../../types").Match
): NormalizedMatch => {
  // Check if it's a LiveMatch (has league_name) or Match (has league object)
  if ("league_name" in match) {
    // It's a LiveMatch
    return {
      status: match.status || "LIVE",
      leagueName: match.league_name || "Liga",
      homeTeamName: match.home_team,
      awayTeamName: match.away_team,
      homeScore: match.home_score ?? 0,
      awayScore: match.away_score ?? 0,
    };
  } else {
    // It's a Match
    return {
      status: match.status || "LIVE",
      leagueName: match.league?.name || "Liga",
      homeTeamName: match.home_team?.name || "Local",
      awayTeamName: match.away_team?.name || "Visitante",
      homeScore: match.home_goals ?? 0,
      awayScore: match.away_goals ?? 0,
    };
  }
};

const LiveMatchCard: React.FC<MatchCardProps> = ({ matchData }) => {
  // Adaptation: The new hook returns flattened match objects (LiveMatch),
  // but this component expects { match, prediction } structure (LiveMatchPrediction).

  // Get raw match and prediction
  const rawMatch = isLiveMatchPrediction(matchData)
    ? matchData.match
    : matchData;
  const prediction = isLiveMatchPrediction(matchData)
    ? matchData.prediction
    : undefined;

  // Normalize match data for uniform access
  const match = normalizeMatch(
    rawMatch as LiveMatch | import("../../../types").Match
  );

  // Determine the recommended result
  const getRecommendation = () => {
    if (!prediction || prediction.confidence === 0) return null;

    const probs = [
      { label: "1", value: validPrediction!.home_win_probability },
      { label: "X", value: validPrediction!.draw_probability },
      { label: "2", value: validPrediction!.away_win_probability },
    ];

    const max = probs.reduce((a, b) => (a.value > b.value ? a : b));
    return max;
  };

  const recommendation = getRecommendation();
  const confidence = prediction?.confidence ?? 0;
  const hasValidPrediction = confidence > 0 && prediction !== undefined;
  // Use non-null assertion since hasValidPrediction guards these usages
  const validPrediction = hasValidPrediction ? prediction! : null;

  // Parse status for display (e.g., "1H", "2H", "HT", "90'")
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
        // Pulsing animation for live indicator
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
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
          >
            <Chip
              icon={<AccessTime sx={{ fontSize: 14 }} />}
              label={displayStatus}
              size="small"
              color="error"
              sx={{
                height: 22,
                fontSize: "0.7rem",
                fontWeight: 600,
                ml: 2,
              }}
            />
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{
                maxWidth: 120,
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {match.leagueName}
            </Typography>
          </Box>

          {/* Teams and Score */}
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
          >
            <Box flex={1} textAlign="left">
              <Typography
                fontWeight={500}
                sx={{
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {match.homeTeamName}
              </Typography>
            </Box>

            <Box
              sx={{
                px: 2,
                py: 0.75,
                bgcolor: "rgba(0, 0, 0, 0.4)",
                borderRadius: 1.5,
                minWidth: 70,
                textAlign: "center",
              }}
            >
              <Typography variant="h6" fontWeight="bold" color="primary.light">
                {match.homeScore} - {match.awayScore}
              </Typography>
            </Box>

            <Box flex={1} textAlign="right">
              <Typography
                fontWeight={500}
                sx={{
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {match.awayTeamName}
              </Typography>
            </Box>
          </Box>

          {/* Prediction Section */}
          {hasValidPrediction ? (
            <Fade in timeout={500}>
              <Box>
                {/* Probability Bar */}
                <Box display="flex" alignItems="center" gap={1} mb={1}>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    width={24}
                  >
                    1
                  </Typography>
                  <Box flex={1} position="relative">
                    <LinearProgress
                      variant="determinate"
                      value={100}
                      sx={{
                        height: 6,
                        borderRadius: 3,
                        bgcolor: "rgba(148, 163, 184, 0.15)",
                        "& .MuiLinearProgress-bar": {
                          background: `linear-gradient(90deg, 
                            #10b981 0%, 
                            #10b981 ${
                              validPrediction!.home_win_probability * 100
                            }%, 
                            #6366f1 ${
                              validPrediction!.home_win_probability * 100
                            }%, 
                            #6366f1 ${
                              (validPrediction!.home_win_probability +
                                validPrediction!.draw_probability) *
                              100
                            }%,
                            #ef4444 ${
                              (validPrediction!.home_win_probability +
                                validPrediction!.draw_probability) *
                              100
                            }%,
                            #ef4444 100%
                          )`,
                          borderRadius: 3,
                        },
                      }}
                    />
                  </Box>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    width={24}
                  >
                    2
                  </Typography>
                </Box>

                {/* Probability Labels */}
                <Box display="flex" justifyContent="space-between" mb={1}>
                  <Tooltip title="Probabilidad Victoria Local">
                    <Chip
                      label={`1: ${(
                        validPrediction!.home_win_probability * 100
                      ).toFixed(0)}%`}
                      size="small"
                      sx={{
                        bgcolor:
                          recommendation?.label === "1"
                            ? "rgba(16, 185, 129, 0.2)"
                            : "transparent",
                        border:
                          recommendation?.label === "1"
                            ? "1px solid #10b981"
                            : "1px solid rgba(148, 163, 184, 0.2)",
                        fontSize: "0.65rem",
                        height: 20,
                      }}
                    />
                  </Tooltip>
                  <Tooltip title="Probabilidad Empate">
                    <Chip
                      label={`X: ${(
                        validPrediction!.draw_probability * 100
                      ).toFixed(0)}%`}
                      size="small"
                      sx={{
                        bgcolor:
                          recommendation?.label === "X"
                            ? "rgba(99, 102, 241, 0.2)"
                            : "transparent",
                        border:
                          recommendation?.label === "X"
                            ? "1px solid #6366f1"
                            : "1px solid rgba(148, 163, 184, 0.2)",
                        fontSize: "0.65rem",
                        height: 20,
                      }}
                    />
                  </Tooltip>
                  <Tooltip title="Probabilidad Victoria Visitante">
                    <Chip
                      label={`2: ${(
                        validPrediction!.away_win_probability * 100
                      ).toFixed(0)}%`}
                      size="small"
                      sx={{
                        bgcolor:
                          recommendation?.label === "2"
                            ? "rgba(239, 68, 68, 0.2)"
                            : "transparent",
                        border:
                          recommendation?.label === "2"
                            ? "1px solid #ef4444"
                            : "1px solid rgba(148, 163, 184, 0.2)",
                        fontSize: "0.65rem",
                        height: 20,
                      }}
                    />
                  </Tooltip>
                </Box>

                {/* Confidence */}
                <Box
                  display="flex"
                  alignItems="center"
                  justifyContent="space-between"
                >
                  <Box display="flex" alignItems="center" gap={0.5}>
                    <TrendingUp
                      sx={{ fontSize: 14, color: "secondary.main" }}
                    />
                    <Typography variant="caption" color="text.secondary">
                      Confianza: {(confidence * 100).toFixed(0)}%
                    </Typography>
                  </Box>
                  {validPrediction!.over_25_probability > 0.5 && (
                    <Chip
                      icon={<SportsScore sx={{ fontSize: 12 }} />}
                      label={`+2.5: ${(
                        validPrediction!.over_25_probability * 100
                      ).toFixed(0)}%`}
                      size="small"
                      color="warning"
                      variant="outlined"
                      sx={{ fontSize: "0.6rem", height: 18 }}
                    />
                  )}
                </Box>
              </Box>
            </Fade>
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
};

/**
 * Main LiveMatches Component
 */
const LiveMatches: React.FC = () => {
  const { matches, loading, error, refresh } = useLiveMatches();

  // Compat for old hook props
  const refreshing = loading;
  const processingMessage = "";

  // Show processing message during initial load
  if (loading && processingMessage) {
    return (
      <Box my={4}>
        <Box display="flex" alignItems="center" gap={1} mb={2}>
          <LiveTv color="error" />
          <Typography variant="h6" fontWeight={600}>
            Partidos en Vivo
          </Typography>
        </Box>

        {/* Processing Message Card */}
        <Card
          sx={{
            background: "rgba(99, 102, 241, 0.1)",
            backdropFilter: "blur(10px)",
            border: "1px solid rgba(99, 102, 241, 0.3)",
            borderRadius: 2,
            mb: 3,
          }}
        >
          <CardContent
            sx={{ py: 2, display: "flex", alignItems: "center", gap: 2 }}
          >
            <CircularProgress size={24} color="primary" />
            <Typography color="primary.light" fontWeight={500}>
              {processingMessage}
            </Typography>
          </CardContent>
        </Card>

        {/* Skeleton Grid */}
        <Grid container spacing={2}>
          {[...Array(3)].map((_, i) => (
            <Grid size={{ xs: 12, md: 6, lg: 4 }} key={i}>
              <MatchCardSkeleton />
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  }

  // Hide section if no live matches or error
  if (error || matches.length === 0) {
    return null;
  }

  return (
    <Box my={4}>
      {/* Header */}
      <Box
        display="flex"
        alignItems="center"
        justifyContent="space-between"
        mb={2}
      >
        <Box display="flex" alignItems="center" gap={1}>
          <LiveTv color="error" />
          <Typography variant="h6" fontWeight={600}>
            Partidos en Vivo
          </Typography>
          <Chip
            label={matches.length}
            color="error"
            size="small"
            sx={{ height: 22, fontSize: "0.75rem", fontWeight: 600 }}
          />
        </Box>

        <Box display="flex" alignItems="center" gap={1}>
          {/* lastUpdated time removed per user request */}
          <Tooltip title="Actualizar">
            <IconButton
              size="small"
              onClick={refresh}
              disabled={refreshing}
              sx={{ color: "text.secondary" }}
            >
              <Refresh
                sx={{
                  fontSize: 18,
                  animation: refreshing ? "spin 1s linear infinite" : "none",
                }}
              />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {/* Refreshing indicator */}
      {refreshing && (
        <LinearProgress
          sx={{
            mb: 2,
            borderRadius: 1,
            height: 2,
          }}
        />
      )}

      {/* Matches Grid */}
      <Grid container spacing={2}>
        {matches.map((matchData) => (
          <Grid
            size={{ xs: 12, md: 6, lg: 4 }}
            key={
              "id" in matchData
                ? matchData.id
                : (matchData as LiveMatchPrediction).match?.id
            }
          >
            <LiveMatchCard matchData={matchData} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default LiveMatches;

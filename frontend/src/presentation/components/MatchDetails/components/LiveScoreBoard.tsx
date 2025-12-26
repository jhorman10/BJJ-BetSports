import React from "react";
import { Box, Typography, Paper, Chip } from "@mui/material";
import { Timer } from "@mui/icons-material";
import { Match, MatchEvent } from "../../../../domain/entities/match";

interface LiveScoreBoardProps {
  match: Match;
}

export const LiveScoreBoard: React.FC<LiveScoreBoardProps> = ({ match }) => {
  const getGoalEvents = (teamId: string) =>
    match.events
      ?.filter(
        (e: MatchEvent) =>
          e.type === "Goal" &&
          e.team_id === teamId &&
          e.detail !== "Missed Penalty"
      )
      .map((e: MatchEvent, i: number) => (
        <Typography
          key={i}
          variant="caption"
          display="block"
          color="text.secondary"
          sx={{ lineHeight: 1.2 }}
        >
          ⚽ {e.player_name} ({e.time}')
        </Typography>
      ));

  return (
    <Paper
      elevation={3}
      sx={{
        p: 3,
        mb: 3,
        background: "rgba(255, 255, 255, 0.05)",
        backdropFilter: "blur(10px)",
        borderRadius: 2,
        border: "1px solid rgba(255, 255, 255, 0.1)",
      }}
    >
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        mb={2}
      >
        {/* Home Team */}
        <Box textAlign="center" flex={1}>
          <Typography
            variant="h6"
            fontWeight="bold"
            sx={{
              height: 48,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {match.home_team.name}
          </Typography>
        </Box>

        {/* Score & Time */}
        <Box textAlign="center" px={2}>
          <Box
            display="flex"
            flexDirection="column"
            alignItems="center"
            gap={0.5}
            mb={1}
          >
            <Chip
              icon={<Timer sx={{ fontSize: "1.2rem !important" }} />}
              label={match.status}
              color={match.status === "LIVE" ? "error" : "default"}
              sx={{
                fontWeight: "bold",
                px: 1,
                animation:
                  match.status === "LIVE" ? "pulse 2s infinite" : "none",
                "@keyframes pulse": {
                  "0%": { opacity: 1 },
                  "50%": { opacity: 0.7 },
                  "100%": { opacity: 1 },
                },
              }}
            />
            {/* Big Visible Clock */}
            {match.minute && (
              <Typography
                variant="h4"
                color="#4ade80"
                fontWeight="900"
                sx={{ fontFamily: "monospace", letterSpacing: 1 }}
              >
                {match.minute}'
              </Typography>
            )}
          </Box>

          <Typography variant="h2" fontWeight="900" sx={{ letterSpacing: 4 }}>
            {match.home_goals ?? 0} - {match.away_goals ?? 0}
          </Typography>
        </Box>

        {/* Away Team */}
        <Box textAlign="center" flex={1}>
          <Typography
            variant="h6"
            fontWeight="bold"
            sx={{
              height: 48,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {match.away_team.name}
          </Typography>
        </Box>
      </Box>

      {/* Scorers Row */}
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="flex-start"
      >
        <Box flex={1} textAlign="left" pl={1}>
          {getGoalEvents(match.home_team.id)}
        </Box>
        <Box flex={1} textAlign="right" pr={1}>
          {getGoalEvents(match.away_team.id)}
        </Box>
      </Box>
    </Paper>
  );
};

import React from "react";
import {
  Box,
  Typography,
  Paper,
  Chip,
  useTheme,
  useMediaQuery,
} from "@mui/material";
import { Timer } from "@mui/icons-material";
import { Match, MatchEvent } from "../../../../domain/entities/match";

interface LiveScoreBoardProps {
  match: Match;
}

export const LiveScoreBoard: React.FC<LiveScoreBoardProps> = ({ match }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

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
          sx={{ lineHeight: 1.2, fontSize: isMobile ? "0.7rem" : "0.75rem" }}
        >
          ⚽ {e.player_name} ({e.time}')
        </Typography>
      ));

  return (
    <Paper
      elevation={3}
      sx={{
        p: { xs: 1.5, sm: 3 }, // Reduced padding on mobile
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
        flexDirection={isMobile ? "column" : "row"}
        gap={isMobile ? 2 : 0}
      >
        {/* Home Team */}
        <Box
          textAlign="center"
          flex={1}
          width="100%"
          order={isMobile ? 2 : 1}
          display="flex"
          justifyContent="center"
          alignItems="center"
        >
          {isMobile && match.home_team.logo_url && (
            <Box
              component="img"
              src={match.home_team.logo_url}
              sx={{ width: 30, height: 30, mr: 1, objectFit: "contain" }}
            />
          )}
          <Typography
            variant={isMobile ? "body1" : "h6"}
            fontWeight="bold"
            sx={{
              lineHeight: 1.2,
            }}
          >
            {match.home_team.name}
          </Typography>
        </Box>

        {/* Score & Time - Center */}
        <Box textAlign="center" px={2} order={isMobile ? 1 : 2} minWidth={120}>
          <Box
            display="flex"
            flexDirection="column"
            alignItems="center"
            gap={0.5}
            mb={1}
          >
            <Chip
              icon={<Timer sx={{ fontSize: "1rem !important" }} />}
              label={match.status}
              color={match.status === "LIVE" ? "error" : "default"}
              size="small"
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
                variant={isMobile ? "h5" : "h4"}
                color="#4ade80"
                fontWeight="900"
                sx={{ fontFamily: "monospace", letterSpacing: 1 }}
              >
                {match.minute}'
              </Typography>
            )}
          </Box>

          <Typography
            variant={isMobile ? "h3" : "h2"}
            fontWeight="900"
            sx={{ letterSpacing: isMobile ? 2 : 4 }}
          >
            {match.home_goals ?? 0} - {match.away_goals ?? 0}
          </Typography>
        </Box>

        {/* Away Team */}
        <Box
          textAlign="center"
          flex={1}
          width="100%"
          order={isMobile ? 3 : 3}
          display="flex"
          justifyContent="center"
          alignItems="center"
        >
          <Typography
            variant={isMobile ? "body1" : "h6"}
            fontWeight="bold"
            sx={{
              lineHeight: 1.2,
            }}
          >
            {match.away_team.name}
          </Typography>
          {isMobile && match.away_team.logo_url && (
            <Box
              component="img"
              src={match.away_team.logo_url}
              sx={{ width: 30, height: 30, ml: 1, objectFit: "contain" }}
            />
          )}
        </Box>
      </Box>

      {/* Scorers Row - Conditional display or simplified */}
      {getGoalEvents(match.home_team.id)?.length ||
      getGoalEvents(match.away_team.id)?.length ? (
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="flex-start"
          mt={2}
          pt={2}
          borderTop="1px solid rgba(255,255,255,0.1)"
        >
          <Box flex={1} textAlign="left" pl={1}>
            {getGoalEvents(match.home_team.id)}
          </Box>
          <Box flex={1} textAlign="right" pr={1}>
            {getGoalEvents(match.away_team.id)}
          </Box>
        </Box>
      ) : null}
    </Paper>
  );
};

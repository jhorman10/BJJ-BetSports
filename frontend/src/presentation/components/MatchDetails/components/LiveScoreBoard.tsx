import React from "react";
import {
  Box,
  Typography,
  Paper,
  Chip,
  useTheme,
  useMediaQuery,
  styled,
} from "@mui/material";
import { Match, MatchEvent } from "../../../../domain/entities/match";

// --- Estilos Compartidos con LiveMatchCard ---
const PulseDot = styled(Box)({
  width: 6,
  height: 6,
  borderRadius: "50%",
  backgroundColor: "#22c55e",
  animation: "pulse 1.5s infinite ease-in-out",
  willChange: "opacity",
  "@keyframes pulse": {
    "0%": { opacity: 1 },
    "50%": { opacity: 0.4 },
    "100%": { opacity: 1 },
  },
});

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
        mb={3}
        flexDirection="row"
        gap={1}
      >
        {/* Home Team */}
        <Box
          textAlign="center"
          flex={1}
          display="flex"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
        >
          {match.home_team.logo_url && (
            <Box
              component="img"
              src={match.home_team.logo_url}
              sx={{
                width: isMobile ? 32 : 48,
                height: isMobile ? 32 : 48,
                mb: 1,
                objectFit: "contain",
              }}
            />
          )}
          <Typography
            variant={isMobile ? "caption" : "body1"}
            fontWeight="bold"
            sx={{
              lineHeight: 1.1,
              textAlign: "center",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
              maxWidth: "100%",
              color: "white",
            }}
          >
            {match.home_team.name}
          </Typography>
        </Box>

        {/* Score & Time - Center */}
        <Box
          display="flex"
          flexDirection="column"
          alignItems="center"
          gap={1.5}
          sx={{ minWidth: isMobile ? 100 : 150 }}
        >
          {/* Status & Time Row */}
          <Box display="flex" alignItems="center" gap={1}>
            <Chip
              label={
                match.status === "LIVE" || match.status === "IN_PLAY"
                  ? "LIVE"
                  : match.status
              }
              color={
                match.status === "LIVE" || match.status === "IN_PLAY"
                  ? "error"
                  : match.status === "HT"
                  ? "warning"
                  : "default"
              }
              size="small"
              sx={{
                height: 18,
                fontSize: "0.6rem",
                fontWeight: "bold",
                px: 0.5,
                "& .MuiChip-label": { px: 1 },
              }}
            />

            {/* Time Badge */}
            {match.minute && (
              <Box
                display="flex"
                alignItems="center"
                gap={1}
                sx={{
                  bgcolor: "rgba(34, 197, 94, 0.1)",
                  px: 1,
                  py: 0.25,
                  borderRadius: "100px",
                  border: "1px solid rgba(34, 197, 94, 0.2)",
                }}
              >
                <PulseDot />
                <Typography
                  variant="caption"
                  fontWeight={700}
                  color="#4ade80"
                  sx={{ fontFamily: "monospace", lineHeight: 1 }}
                >
                  {match.minute}'
                </Typography>
              </Box>
            )}
          </Box>

          {/* Score Box Style from LiveMatchCard */}
          <Box
            sx={{
              px: isMobile ? 2 : 3,
              py: isMobile ? 0.5 : 1,
              bgcolor: "rgba(0,0,0,0.3)",
              borderRadius: "12px",
              border: "1px solid rgba(255,255,255,0.05)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Typography
              variant={isMobile ? "h5" : "h4"}
              fontWeight={700}
              color="white"
            >
              {match.home_goals ?? 0}
            </Typography>
            <Typography
              variant={isMobile ? "h6" : "h5"}
              sx={{
                mx: isMobile ? 1 : 1.5,
                color: "rgba(255,255,255,0.3)",
                pb: 0.5,
                lineHeight: 1,
              }}
            >
              :
            </Typography>
            <Typography
              variant={isMobile ? "h5" : "h4"}
              fontWeight={700}
              color="white"
            >
              {match.away_goals ?? 0}
            </Typography>
          </Box>
        </Box>

        {/* Away Team */}
        <Box
          textAlign="center"
          flex={1}
          display="flex"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
        >
          {match.away_team.logo_url && (
            <Box
              component="img"
              src={match.away_team.logo_url}
              sx={{
                width: isMobile ? 32 : 48,
                height: isMobile ? 32 : 48,
                mb: 1,
                objectFit: "contain",
              }}
            />
          )}
          <Typography
            variant={isMobile ? "caption" : "body1"}
            fontWeight="bold"
            sx={{
              lineHeight: 1.1,
              textAlign: "center",
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow: "hidden",
              maxWidth: "100%",
              color: "white",
            }}
          >
            {match.away_team.name}
          </Typography>
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

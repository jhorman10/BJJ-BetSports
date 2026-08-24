import React, { memo } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  styled,
  Chip,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import { Flag, QueryStats, SportsSoccer } from "@mui/icons-material";

import { LiveMatchRaw } from "../../../utils/matchMatching";
import { getLeagueName } from "../LeagueSelector/constants";
import { cleanTeamName } from "../../../utils/teamUtils";
import { TeamLogo } from "../common/TeamLogo";

// --- Estilos Ultra Premium ---
const MatchCard = styled(Card)(() => ({
  background:
    "linear-gradient(165deg, rgba(20, 25, 35, 0.85) 0%, rgba(10, 14, 23, 0.95) 100%)", // Darker, richer
  backdropFilter: "blur(24px)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  borderRadius: "28px", // Slightly softer corners
  position: "relative",
  overflow: "hidden",
  transition: "all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1)",
  cursor: "pointer",
  boxShadow:
    "0 15px 35px -5px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255,255,255,0.1), inset 0 0 20px rgba(0,0,0,0.2)",
  "&:hover": {
    transform: "translateY(-6px) scale(1.01)",
    boxShadow:
      "0 25px 50px -12px rgba(0, 0, 0, 0.6), inset 0 1px 0 rgba(255,255,255,0.2)",
    borderColor: "rgba(74, 222, 128, 0.3)", // Greenish tint on hover
    "& .action-bg": {
      opacity: 1,
    },
  },
}));

const PulseDot = styled(Box)({
  width: 6,
  height: 6,
  borderRadius: "50%",
  backgroundColor: "#00e676", // Brighter green
  boxShadow: "0 0 10px 2px rgba(0, 230, 118, 0.6)",
  animation: "pulse 1.8s infinite ease-in-out",
  willChange: "opacity",
  "@keyframes pulse": {
    "0%": { opacity: 1, transform: "scale(1)" },
    "50%": { opacity: 0.6, transform: "scale(1.2)" },
    "100%": { opacity: 1, transform: "scale(1)" },
  },
});

const CardBadge = styled(Box)<{ color: string }>(({ color }) => ({
  width: 8,
  height: 8,
  backgroundColor: color,
  borderRadius: "2px",
  boxShadow: `0 0 8px ${color}`, // Glow effect
}));

interface LiveMatchCardProps {
  match: LiveMatchRaw;
  onMatchClick?: (match: LiveMatchRaw) => void;
}

const LiveMatchCard: React.FC<LiveMatchCardProps> = memo(
  ({ match, onMatchClick }) => {
    return (
      <Grid size={{ xs: 12, sm: 6, md: 6, lg: 4 }}>
        <MatchCard onClick={() => onMatchClick?.(match)}>
          {/* Background Accent (for hover) */}
          <Box
            className="action-bg"
            sx={{
              position: "absolute",
              inset: 0,
              background:
                "radial-gradient(800px circle at var(--mouse-x) var(--mouse-y), rgba(255,255,255,0.03), transparent 40%)",
              opacity: 0,
              transition: "opacity 0.4s",
              pointerEvents: "none",
            }}
          />

          <CardContent
            sx={{ p: { xs: "16px !important", sm: "24px !important" }, position: "relative", zIndex: 1 }}
          >
            {/* Header: Liga + Tiempo */}
            <Box
              display="flex"
              justifyContent="space-between"
              alignItems="center"
              mb={4}
            >
              <Box display="flex" alignItems="center" gap={1.5}>
                {match.league_flag && (
                  <Box
                    component="img"
                    src={match.league_flag}
                    alt={match.league_name}
                    sx={{
                      width: 18,
                      height: 18,
                      borderRadius: "50%",
                      objectFit: "cover",
                      border: "1px solid rgba(255,255,255,0.15)",
                    }}
                  />
                )}
                <Typography
                  variant="caption"
                  color="rgba(255,255,255,0.7)"
                  fontWeight={700}
                  sx={{
                    textTransform: "uppercase",
                    fontSize: { xs: "0.65rem", sm: "0.6rem" },
                    letterSpacing: "1px",
                    textShadow: "0 1px 2px rgba(0,0,0,0.5)",
                  }}
                >
                  {getLeagueName(match.league_name)}
                </Typography>
              </Box>

              <Box display="flex" alignItems="center" gap={1}>
                {match.status === "HT" && (
                  <Chip
                    label="HT"
                    size="small"
                    sx={{
                      height: 20,
                      fontSize: "0.6rem",
                      fontWeight: 800,
                      bgcolor: "rgba(245, 158, 11, 0.2)",
                      color: "#fbbf24",
                      border: "1px solid rgba(245, 158, 11, 0.4)",
                      mr: 0.5,
                    }}
                  />
                )}
                <Box
                  display="flex"
                  alignItems="center"
                  gap={1}
                  sx={{
                    bgcolor: "rgba(0, 0, 0, 0.3)",
                    px: 1.5,
                    py: 0.5,
                    borderRadius: "100px",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                  }}
                >
                  <PulseDot />
                  <Typography
                    variant="caption"
                    fontWeight={700}
                    color="#00e676"
                    sx={{ fontFamily: "monospace", letterSpacing: 1 }}
                  >
                    {match.minute}'
                  </Typography>
                </Box>
              </Box>
            </Box>

            {/* Scoreboard Central */}
            <Box
              display="grid"
              gridTemplateColumns="1fr auto 1fr"
              alignItems="center"
              mb={3}
              position="relative"
              sx={{ overflow: "hidden" }}
            >
              {/* Home Team */}
              <Box
                display="flex"
                flexDirection="column"
                alignItems="center"
                justifyContent="center"
                zIndex={2}
                sx={{ minWidth: 0, overflow: "hidden" }}
              >
                <Box
                  sx={{
                    position: "relative",
                    mb: 1,
                    filter: "drop-shadow(0 6px 8px rgba(0,0,0,0.4))",
                  }}
                >
                  {match.home_logo_url ? (
                    <TeamLogo
                      src={match.home_logo_url}
                      alt={cleanTeamName(
                        match.home_short_name || match.home_team
                      )}
                      width={42}
                      height={42}
                      sx={{
                        transition: "transform 0.3s",
                        "&:hover": { transform: "scale(1.1)" },
                      }}
                    />
                  ) : (
                    <SportsSoccer
                      sx={{ fontSize: 36, color: "rgba(255,255,255,0.1)" }}
                    />
                  )}
                </Box>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="white"
                  align="center"
                  sx={{
                    lineHeight: 1.2,
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                    fontSize: "0.85rem",
                    textShadow: "0 2px 4px rgba(0,0,0,0.8)",
                    px: 1,
                    letterSpacing: "0.2px",
                  }}
                >
                  {cleanTeamName(match.home_short_name || match.home_team)}
                </Typography>
              </Box>

              {/* Score - Clean & Large */}
              <Box
                display="flex"
                alignItems="center"
                justifyContent="center"
                sx={{ px: { xs: 0.5, sm: 1 }, zIndex: 2, flexShrink: 0 }}
              >
                <Typography
                  variant="h3"
                  fontWeight={800}
                  color="white"
                  sx={{
                    fontSize: "1.5rem",
                    lineHeight: 1,
                    textShadow:
                      "0 0 20px rgba(255,255,255,0.15), 0 4px 10px rgba(0,0,0,0.5)",
                    fontFeatureSettings: "'tnum'",
                  }}
                >
                  {match.home_score}
                </Typography>
                <Typography
                  variant="h4"
                  sx={{
                    mx: { xs: 0.5, sm: 1.5 },
                    color: "rgba(255,255,255,0.15)",
                    fontWeight: 200,
                    fontSize: { xs: "1rem", sm: "1.25rem" },
                    lineHeight: 1,
                    mb: 0.5, // Subtle optical adjustment
                  }}
                >
                  -
                </Typography>
                <Typography
                  variant="h3"
                  fontWeight={800}
                  color="white"
                  sx={{
                    fontSize: "1.5rem",
                    lineHeight: 1,
                    textShadow:
                      "0 0 20px rgba(255,255,255,0.15), 0 4px 10px rgba(0,0,0,0.5)",
                    fontFeatureSettings: "'tnum'",
                  }}
                >
                  {match.away_score}
                </Typography>
              </Box>

              {/* Away Team */}
              <Box
                display="flex"
                flexDirection="column"
                alignItems="center"
                justifyContent="center"
                zIndex={2}
                sx={{ minWidth: 0, overflow: "hidden" }}
              >
                <Box
                  sx={{
                    position: "relative",
                    mb: 1,
                    filter: "drop-shadow(0 6px 8px rgba(0,0,0,0.4))",
                  }}
                >
                  {match.away_logo_url ? (
                    <TeamLogo
                      src={match.away_logo_url}
                      alt={cleanTeamName(
                        match.away_short_name || match.away_team
                      )}
                      width={42}
                      height={42}
                      sx={{
                        transition: "transform 0.3s",
                        "&:hover": { transform: "scale(1.1)" },
                      }}
                    />
                  ) : (
                    <SportsSoccer
                      sx={{ fontSize: 36, color: "rgba(255,255,255,0.1)" }}
                    />
                  )}
                </Box>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="white"
                  align="center"
                  sx={{
                    lineHeight: 1.2,
                    display: "-webkit-box",
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: "vertical",
                    overflow: "hidden",
                    fontSize: "0.85rem",
                    textShadow: "0 2px 4px rgba(0,0,0,0.8)",
                    px: 1,
                    letterSpacing: "0.2px",
                  }}
                >
                  {cleanTeamName(match.away_short_name || match.away_team)}
                </Typography>
              </Box>
            </Box>

            {/* Stats Section */}
            <Box
              sx={{
                background: "rgba(15, 23, 42, 0.4)",
                borderRadius: "16px",
                py: { xs: 1, sm: 1.5 },
                px: { xs: 1, sm: 2 },
                border: "1px solid rgba(255,255,255,0.05)",
                mt: "auto",
              }}
            >
              {/* Possession Bar */}
              {(match.home_possession || match.away_possession) && (
                <Box mb={1.5}>
                  <Box display="flex" justifyContent="space-between" mb={0.5} gap={0.5}>
                    <Typography
                      variant="body2"
                      fontWeight={700}
                      color="white"
                      sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
                    >
                      {match.home_possession ?? "50%"}
                    </Typography>
                    <Typography
                      variant="caption"
                      color="rgba(255,255,255,0.6)"
                      sx={{ flexShrink: 0, fontSize: { xs: "0.65rem", sm: "0.7rem" } }}
                    >
                      Posesión
                    </Typography>
                    <Typography
                      variant="body2"
                      fontWeight={700}
                      color="white"
                      sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
                    >
                      {match.away_possession ?? "50%"}
                    </Typography>
                  </Box>
                  <Box
                    sx={{
                      display: "flex",
                      height: 4,
                      borderRadius: 1,
                      overflow: "hidden",
                      bgcolor: "rgba(255,255,255,0.05)",
                    }}
                  >
                    <Box
                      sx={{
                        width: match.home_possession || "50%",
                        minWidth: "20px",
                        bgcolor: "#6366f1",
                        transition: "width 0.3s ease",
                        borderRadius: 1,
                      }}
                    />
                    <Box
                      sx={{
                        width: match.away_possession || "50%",
                        minWidth: "20px",
                        bgcolor: "#f43f5e",
                        transition: "width 0.3s ease",
                        borderRadius: 1,
                      }}
                    />
                  </Box>
                </Box>
              )}

              {/* Total Shots */}
              {(match.home_total_shots != null || match.away_total_shots != null) && (
                <Box
                  display="flex"
                  justifyContent="space-between"
                  alignItems="center"
                  mb={1}
                  gap={0.5}
                  sx={{ borderBottom: "1px solid rgba(255,255,255,0.05)", pb: 1 }}
                >
                  <Typography
                    variant="body2"
                    fontWeight={700}
                    color="white"
                    sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
                  >
                    {match.home_total_shots ?? 0}
                    {match.home_shots_on_target != null && ` (${match.home_shots_on_target})`}
                  </Typography>
                  <Box display="flex" alignItems="center" gap={0.3} sx={{ flexShrink: 0 }}>
                    <QueryStats sx={{ fontSize: { xs: 10, sm: 12 }, color: "#6366f1", opacity: 0.8 }} />
                    <Typography
                      variant="caption"
                      color="rgba(255,255,255,0.6)"
                      sx={{ fontSize: { xs: "0.65rem", sm: "0.7rem" }, whiteSpace: "nowrap" }}
                    >
                      Tiros{(match.home_shots_on_target != null || match.away_shots_on_target != null) ? " (Al Arco)" : ""}
                    </Typography>
                  </Box>
                  <Typography
                    variant="body2"
                    fontWeight={700}
                    color="white"
                    sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
                  >
                    {match.away_total_shots ?? 0}
                    {match.away_shots_on_target != null && ` (${match.away_shots_on_target})`}
                  </Typography>
                </Box>
              )}

              {/* Corners */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={1}
                gap={0.5}
                sx={{ borderBottom: "1px solid rgba(255,255,255,0.05)", pb: 1 }}
              >
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="white"
                  sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
                >
                  {match.home_corners ?? 0}
                </Typography>
                <Box display="flex" alignItems="center" gap={0.3} sx={{ flexShrink: 0 }}>
                  <Flag sx={{ fontSize: { xs: 10, sm: 12 }, color: "#fbbf24", opacity: 0.8 }} />
                  <Typography
                    variant="caption"
                    color="rgba(255,255,255,0.6)"
                    sx={{ fontSize: { xs: "0.65rem", sm: "0.7rem" } }}
                  >
                    Córners
                  </Typography>
                </Box>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="white"
                  sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
                >
                  {match.away_corners ?? 0}
                </Typography>
              </Box>

              {/* Yellow Cards */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={1}
                gap={0.5}
                sx={{ borderBottom: "1px solid rgba(255,255,255,0.05)", pb: 1 }}
              >
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="white"
                  sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
                >
                  {match.home_yellow_cards ?? 0}
                </Typography>
                <Box display="flex" alignItems="center" gap={0.3} sx={{ flexShrink: 0 }}>
                  <CardBadge color="#facc15" />
                  <Typography
                    variant="caption"
                    color="rgba(255,255,255,0.6)"
                    sx={{ fontSize: { xs: "0.65rem", sm: "0.7rem" } }}
                  >
                    T. Amarillas
                  </Typography>
                </Box>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="white"
                  sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
                >
                  {match.away_yellow_cards ?? 0}
                </Typography>
              </Box>

              {/* Red Cards */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={1}
                gap={0.5}
                sx={{ borderBottom: "1px solid rgba(255,255,255,0.05)", pb: 1 }}
              >
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="white"
                  sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
                >
                  {match.home_red_cards ?? 0}
                </Typography>
                <Box display="flex" alignItems="center" gap={0.3} sx={{ flexShrink: 0 }}>
                  <CardBadge color="#ef4444" />
                  <Typography
                    variant="caption"
                    color="rgba(255,255,255,0.6)"
                    sx={{ fontSize: { xs: "0.65rem", sm: "0.7rem" } }}
                  >
                    T. Rojas
                  </Typography>
                </Box>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="white"
                  sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
                >
                  {match.away_red_cards ?? 0}
                </Typography>
              </Box>

              {/* Disciplina Section Header */}
              <Box mt={1} mb={0.5}>
                <Typography
                  variant="caption"
                  fontWeight={700}
                  color="rgba(255,255,255,0.5)"
                  sx={{
                    textTransform: "uppercase",
                    letterSpacing: "1px",
                    fontSize: "0.7rem",
                    display: "block",
                    textAlign: "center",
                    borderBottom: "1px solid rgba(255,255,255,0.05)",
                    pb: 0.5,
                  }}
                >
                  Disciplina
                </Typography>
              </Box>

              {/* Fouls */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={0.5}
                gap={0.5}
              >
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="white"
                  sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
                >
                  {match.home_fouls ?? 0}
                </Typography>
                <Typography
                  variant="caption"
                  color="rgba(255,255,255,0.6)"
                  sx={{ flexShrink: 0, fontSize: { xs: "0.65rem", sm: "0.7rem" } }}
                >
                  Faltas
                </Typography>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="white"
                  sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
                >
                  {match.away_fouls ?? 0}
                </Typography>
              </Box>

              {/* Offsides */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                gap={0.5}
              >
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="white"
                  sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
                >
                  {match.home_offsides ?? 0}
                </Typography>
                <Typography
                  variant="caption"
                  color="rgba(255,255,255,0.6)"
                  sx={{ flexShrink: 0, fontSize: { xs: "0.65rem", sm: "0.7rem" } }}
                >
                  Offsides
                </Typography>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="white"
                  sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
                >
                  {match.away_offsides ?? 0}
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </MatchCard>
      </Grid>
    );
  }
);

// Fix display name for memoized component
LiveMatchCard.displayName = "LiveMatchCard";

export default LiveMatchCard;

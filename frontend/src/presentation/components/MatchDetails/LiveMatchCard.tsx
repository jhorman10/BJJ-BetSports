import React, { memo } from "react";
import { Box, Typography, Card, CardContent, styled, Chip } from "@mui/material";
import Grid from "@mui/material/Grid";

import { LiveMatchRaw } from "../../../utils/matchMatching";
import { getLeagueName } from "../LeagueSelector/constants";

import { ScoreboardSection } from "./components/ScoreboardSection";
import { StatsBar } from "./components/StatsBar";

const MatchCard = styled(Card)(() => ({
  background:
    "linear-gradient(165deg, rgba(20, 25, 35, 0.85) 0%, rgba(10, 14, 23, 0.95) 100%)",
  backdropFilter: "blur(24px)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  borderRadius: "28px",
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
    borderColor: "rgba(74, 222, 128, 0.3)",
    "& .action-bg": { opacity: 1 },
  },
}));

const PulseDot = styled(Box)({
  width: 6,
  height: 6,
  borderRadius: "50%",
  backgroundColor: "#00e676",
  boxShadow: "0 0 10px 2px rgba(0, 230, 118, 0.6)",
  animation: "pulse 1.8s infinite ease-in-out",
  willChange: "opacity",
  "@keyframes pulse": {
    "0%": { opacity: 1, transform: "scale(1)" },
    "50%": { opacity: 0.6, transform: "scale(1.2)" },
    "100%": { opacity: 1, transform: "scale(1)" },
  },
});

interface LiveMatchCardProps {
  match: LiveMatchRaw;
  onMatchClick?: (match: LiveMatchRaw) => void;
}

const LiveMatchCard: React.FC<LiveMatchCardProps> = memo(
  ({ match, onMatchClick }) => {
    return (
      <Grid size={{ xs: 12, sm: 6, md: 6, lg: 4 }}>
        <MatchCard onClick={() => onMatchClick?.(match)}>
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
          <CardContent sx={{ p: "24px !important", position: "relative", zIndex: 1 }}>
            {/* Header: League + Time */}
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
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
                    fontSize: "0.6rem",
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

            <ScoreboardSection match={match} />
            <StatsBar match={match} />
          </CardContent>
        </MatchCard>
      </Grid>
    );
  }
);

LiveMatchCard.displayName = "LiveMatchCard";

export default LiveMatchCard;

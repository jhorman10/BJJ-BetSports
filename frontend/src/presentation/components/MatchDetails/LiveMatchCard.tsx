import React, { memo } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  styled,
  Chip,
  Divider,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import { Flag } from "@mui/icons-material";
import { LiveMatchRaw } from "../../../utils/matchMatching";
import { getLeagueName } from "../LeagueSelector/constants";

// --- Estilos Personalizados ---
const MatchCard = styled(Card)(() => ({
  background:
    "linear-gradient(145deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)",
  backdropFilter: "blur(12px)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  borderRadius: "20px",
  position: "relative",
  overflow: "hidden",
  transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
  cursor: "pointer",
  boxShadow:
    "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
  "&:hover": {
    transform: "translateY(-4px)",
    boxShadow:
      "0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2)",
    borderColor: "rgba(34, 197, 94, 0.5)",
  },
}));

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

const CardBadge = styled(Box)<{ color: string }>(({ color }) => ({
  width: 10,
  height: 14,
  backgroundColor: color,
  borderRadius: 2,
  boxShadow: "0 1px 2px rgba(0,0,0,0.3)",
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
          <CardContent sx={{ p: "20px !important" }}>
            {/* Header: Liga + Bandera + Tiempo */}
            <Box
              display="flex"
              justifyContent="space-between"
              alignItems="center"
              mb={2}
            >
              <Box display="flex" alignItems="center" gap={1}>
                {match.league_flag && (
                  <Box
                    component="img"
                    src={match.league_flag}
                    alt={match.league_name}
                    sx={{
                      width: 16,
                      height: 12,
                      borderRadius: 0.5,
                      objectFit: "cover",
                    }}
                  />
                )}
                <Typography
                  variant="caption"
                  color="text.secondary"
                  fontWeight={600}
                  sx={{ textTransform: "uppercase", fontSize: "0.65rem" }}
                >
                  {getLeagueName(match.league_name)}
                </Typography>
              </Box>

              <Box display="flex" alignItems="center" gap={1}>
                {match.status === "HT" && (
                  <Chip
                    label="HT"
                    size="small"
                    color="warning"
                    sx={{ height: 18, fontSize: "0.6rem", fontWeight: 700 }}
                  />
                )}
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
                  >
                    {match.minute}'
                  </Typography>
                </Box>
              </Box>
            </Box>

            {/* Scoreboard Central */}
            <Box
              display="flex"
              alignItems="center"
              justifyContent="space-between"
              mb={3}
            >
              {/* Home Team */}
              <Box
                flex={1}
                display="flex"
                flexDirection="column"
                alignItems="flex-start"
              >
                <Box display="flex" alignItems="center" gap={1}>
                  {match.home_logo_url && (
                    <Box
                      component="img"
                      src={match.home_logo_url}
                      alt={match.home_team}
                      sx={{ width: 28, height: 28, objectFit: "contain" }}
                    />
                  )}
                  <Typography
                    variant="body1"
                    fontWeight={600}
                    color="white"
                    sx={{ lineHeight: 1.2 }}
                  >
                    {match.home_team}
                  </Typography>
                </Box>
              </Box>

              {/* Score Box */}
              <Box
                sx={{
                  mx: 2,
                  px: 2,
                  py: 1,
                  bgcolor: "rgba(0,0,0,0.3)",
                  borderRadius: "12px",
                  border: "1px solid rgba(255,255,255,0.05)",
                  display: "flex",
                  alignItems: "center",
                  minWidth: "80px",
                  justifyContent: "center",
                }}
              >
                <Typography variant="h5" fontWeight={700} color="white">
                  {match.home_score}
                </Typography>
                <Typography
                  variant="h6"
                  sx={{
                    mx: 1,
                    color: "rgba(255,255,255,0.3)",
                    pb: 0.5,
                  }}
                >
                  :
                </Typography>
                <Typography variant="h5" fontWeight={700} color="white">
                  {match.away_score}
                </Typography>
              </Box>

              {/* Away Team */}
              <Box
                flex={1}
                display="flex"
                flexDirection="column"
                alignItems="flex-end"
              >
                <Box display="flex" alignItems="center" gap={1}>
                  <Typography
                    variant="body1"
                    fontWeight={600}
                    color="white"
                    align="right"
                    sx={{ lineHeight: 1.2 }}
                  >
                    {match.away_team}
                  </Typography>
                  {match.away_logo_url && (
                    <Box
                      component="img"
                      src={match.away_logo_url}
                      alt={match.away_team}
                      sx={{ width: 28, height: 28, objectFit: "contain" }}
                    />
                  )}
                </Box>
              </Box>
            </Box>

            {/* Estadísticas: Corners y Tarjetas */}
            <Box
              sx={{
                bgcolor: "rgba(255,255,255,0.03)",
                borderRadius: "12px",
                p: 1.5,
                display: "flex",
                flexDirection: "column",
                gap: 1,
              }}
            >
              {/* Corners */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
              >
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="rgba(255,255,255,0.9)"
                  sx={{ width: 20, textAlign: "center" }}
                >
                  {match.home_corners}
                </Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  <Flag
                    sx={{
                      fontSize: 16,
                      color: "#fbbf24",
                      opacity: 0.8,
                    }}
                  />
                  <Typography variant="caption" color="rgba(255,255,255,0.6)">
                    Córners
                  </Typography>
                </Box>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="rgba(255,255,255,0.9)"
                  sx={{ width: 20, textAlign: "center" }}
                >
                  {match.away_corners}
                </Typography>
              </Box>

              <Divider sx={{ borderColor: "rgba(255,255,255,0.05)" }} />

              {/* Yellow Cards */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
              >
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="rgba(255,255,255,0.9)"
                  sx={{ width: 20, textAlign: "center" }}
                >
                  {match.home_yellow_cards}
                </Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  <CardBadge color="#facc15" />
                  <Typography variant="caption" color="rgba(255,255,255,0.6)">
                    Amarillas
                  </Typography>
                </Box>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="rgba(255,255,255,0.9)"
                  sx={{ width: 20, textAlign: "center" }}
                >
                  {match.away_yellow_cards}
                </Typography>
              </Box>

              <Divider sx={{ borderColor: "rgba(255,255,255,0.05)" }} />

              {/* Red Cards */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
              >
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="rgba(255,255,255,0.9)"
                  sx={{ width: 20, textAlign: "center" }}
                >
                  {match.home_red_cards}
                </Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  <CardBadge color="#ef4444" />
                  <Typography variant="caption" color="rgba(255,255,255,0.6)">
                    Rojas
                  </Typography>
                </Box>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="rgba(255,255,255,0.9)"
                  sx={{ width: 20, textAlign: "center" }}
                >
                  {match.away_red_cards}
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

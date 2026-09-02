import React from "react";
import { Box, Typography, Tooltip, Stack } from "@mui/material";
import SportsSoccer from "@mui/icons-material/SportsSoccer";

import type { Match, Prediction } from "../../../types";
import { getTeamLogo, getTeamDisplayName } from "../../../utils/teamUtils";
import { TeamLogo } from "../common/TeamLogo";

interface TeamDisplayProps {
  match: Match;
  prediction: Prediction;
}

export const TeamDisplay: React.FC<TeamDisplayProps> = ({ match, prediction }) => (
  <Box mb={3}>
    <Stack
      direction="row"
      alignItems="flex-start"
      justifyContent="space-between"
      mb={1}
      spacing={1}
    >
      <Box display="flex" flexDirection="column" alignItems="center" sx={{ flex: 1, minWidth: 0 }}>
        <TeamLogo
          src={getTeamLogo(match.home_team)}
          alt={getTeamDisplayName(match.home_team)}
          width={{ xs: 36, sm: 44, md: 48 }}
          height={{ xs: 36, sm: 44, md: 48 }}
          sx={{ mb: 0.5 }}
        />
        <Typography
          variant="body2"
          fontWeight={600}
          sx={{ textAlign: "center", fontSize: { xs: "0.75rem", sm: "0.875rem" }, lineHeight: 1.2, wordBreak: "break-word" }}
        >
          {getTeamDisplayName(match.home_team)}
        </Typography>
        {match.home_spi && (
          <Tooltip title="Soccer Power Index (SPI)">
            <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.6rem" }}>
              SPI: {match.home_spi.toFixed(1)}
            </Typography>
          </Tooltip>
        )}
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ alignSelf: "center", mx: 0.5 }}>
        vs
      </Typography>
      <Box display="flex" flexDirection="column" alignItems="center" sx={{ flex: 1, minWidth: 0 }}>
        <TeamLogo
          src={getTeamLogo(match.away_team)}
          alt={getTeamDisplayName(match.away_team)}
          width={{ xs: 36, sm: 44, md: 48 }}
          height={{ xs: 36, sm: 44, md: 48 }}
          sx={{ mb: 0.5 }}
        />
        <Typography
          variant="body2"
          fontWeight={600}
          sx={{ textAlign: "center", fontSize: { xs: "0.75rem", sm: "0.875rem" }, lineHeight: 1.2, wordBreak: "break-word" }}
        >
          {getTeamDisplayName(match.away_team)}
        </Typography>
        {match.away_spi && (
          <Tooltip title="Soccer Power Index (SPI)">
            <Typography variant="caption" sx={{ color: "text.secondary", fontSize: "0.6rem" }}>
              SPI: {match.away_spi.toFixed(1)}
            </Typography>
          </Tooltip>
        )}
      </Box>
    </Stack>

    <Box
      display="flex"
      justifyContent="space-between"
      alignItems="center"
      px={2}
      py={1}
      borderRadius={1}
      sx={{ bgcolor: "rgba(59, 130, 246, 0.1)" }}
    >
      <Box textAlign="center">
        <Typography variant="h5" color="primary" fontWeight={800} sx={{ textShadow: "0 0 10px rgba(59, 130, 246, 0.5)" }}>
          {prediction.predicted_home_goals.toFixed(1)}
        </Typography>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.7)" }}>Goles esperados</Typography>
      </Box>
      <SportsSoccer sx={{ color: "text.secondary" }} />
      <Box textAlign="center">
        <Typography variant="h5" color="primary" fontWeight={800} sx={{ textShadow: "0 0 10px rgba(59, 130, 246, 0.5)" }}>
          {prediction.predicted_away_goals.toFixed(1)}
        </Typography>
        <Typography variant="caption" sx={{ color: "rgba(255,255,255,0.7)" }}>Goles esperados</Typography>
      </Box>
    </Box>
  </Box>
);

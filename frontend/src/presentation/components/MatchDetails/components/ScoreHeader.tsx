import React from "react";
import { Box, Typography, Chip, Paper, useTheme, useMediaQuery } from "@mui/material";

import { MatchPrediction } from "../../../../types";
import { translateMatchStatus } from "../../../../utils/translationUtils";
import { getTeamLogo, getTeamDisplayName } from "../../../../utils/teamUtils";
import { TeamLogo } from "../../common/TeamLogo";

interface ScoreHeaderProps {
  details: MatchPrediction;
}

export const ScoreHeader: React.FC<ScoreHeaderProps> = ({ details }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  return (
    <Paper
      elevation={0}
      variant="outlined"
      sx={{
        mb: 3,
        p: { xs: 1.5, sm: 2 },
        bgcolor: "rgba(0, 0, 0, 0.2)",
        borderRadius: 2,
        mt: 1,
        border: "1px solid rgba(255, 255, 255, 0.05)",
      }}
    >
      <Box display="flex" justifyContent="space-between" alignItems="center" gap={1}>
        <Box textAlign="center" flex={1} display="flex" flexDirection="column" alignItems="center">
          <TeamLogo src={getTeamLogo(details.match.home_team)} alt={getTeamDisplayName(details.match.home_team)} width={40} height={40} sx={{ mb: 1 }} />
          <Typography variant={isMobile ? "body2" : "subtitle1"} lineHeight={1.2} fontWeight="bold">
            {getTeamDisplayName(details.match.home_team)}
          </Typography>
          {details.match.home_spi && (
            <Typography variant="caption" color="text.secondary">
              SPI: {details.match.home_spi.toFixed(1)}
            </Typography>
          )}
        </Box>

        <Box textAlign="center" px={1} minWidth={80}>
          <Box bgcolor="rgba(0,0,0,0.4)" borderRadius={2} px={2} py={0.5} mb={1} display="inline-block">
            <Typography variant="h5" fontWeight="900" letterSpacing={1}>
              {details.match.home_goals ?? 0}-{details.match.away_goals ?? 0}
            </Typography>
          </Box>
          <Box display="flex" justifyContent="center">
            <Chip
              label={translateMatchStatus(details.match.status)}
              color={["LIVE", "1H", "2H", "HT"].includes(details.match.status) ? "error" : "default"}
              size="small"
              sx={{ fontWeight: "bold", fontSize: "0.7rem", height: 20 }}
            />
          </Box>
        </Box>

        <Box textAlign="center" flex={1} display="flex" flexDirection="column" alignItems="center">
          <TeamLogo src={getTeamLogo(details.match.away_team)} alt={getTeamDisplayName(details.match.away_team)} width={40} height={40} sx={{ mb: 1 }} />
          <Typography variant={isMobile ? "body2" : "subtitle1"} lineHeight={1.2} fontWeight="bold">
            {getTeamDisplayName(details.match.away_team)}
          </Typography>
          {details.match.away_spi && (
            <Typography variant="caption" color="text.secondary">
              SPI: {details.match.away_spi.toFixed(1)}
            </Typography>
          )}
        </Box>
      </Box>
    </Paper>
  );
};

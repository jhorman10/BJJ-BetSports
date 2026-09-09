import React from "react";
import { Box, Typography, Paper } from "@mui/material";

import { MatchPrediction } from "../../../../types";
import { getTeamDisplayName } from "../../../../utils/teamUtils";

interface ProjectedStatsProps {
  details: MatchPrediction;
}

export const ProjectedStats: React.FC<ProjectedStatsProps> = ({ details }) => {
  const rows = [
    {
      label: "Córners",
      home: details.prediction.predicted_home_corners || details.match.home_corners,
      away: details.prediction.predicted_away_corners || details.match.away_corners,
    },
    {
      label: "Amarillas",
      home: details.prediction.predicted_home_yellow_cards || details.match.home_yellow_cards,
      away: details.prediction.predicted_away_yellow_cards || details.match.away_yellow_cards,
    },
    {
      label: "Rojas",
      home: details.prediction.predicted_home_red_cards || details.match.home_red_cards,
      away: details.prediction.predicted_away_red_cards || details.match.away_red_cards,
    },
  ];

  return (
    <>
      <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
        Estadísticas Proyectadas
      </Typography>
      <Paper variant="outlined" sx={{ p: 0, mb: 3, overflow: "hidden" }}>
        <Box bgcolor="rgba(255,255,255,0.03)" p={1.5} display="flex" justifyContent="space-between">
          <Typography variant="caption" fontWeight="bold">
            {getTeamDisplayName(details.match.home_team)}
          </Typography>
          <Typography variant="caption" fontWeight="bold">
            {getTeamDisplayName(details.match.away_team)}
          </Typography>
        </Box>
        {rows.map((row, i) => (
          <Box
            key={row.label}
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            p={1.5}
            borderTop={i > 0 ? "1px solid rgba(255,255,255,0.05)" : "none"}
          >
            <Box width={40} textAlign="center">
              <Typography fontWeight="bold">{row.home ?? "-"}</Typography>
            </Box>
            <Box display="flex" flexDirection="column" alignItems="center">
              <Typography variant="caption" color="text.secondary">{row.label}</Typography>
            </Box>
            <Box width={40} textAlign="center">
              <Typography fontWeight="bold">{row.away ?? "-"}</Typography>
            </Box>
          </Box>
        ))}
      </Paper>
    </>
  );
};

import React from "react";
import { Box, Typography, Paper, Divider, useTheme, useMediaQuery } from "@mui/material";

import { MatchPrediction } from "../../../../types";
import { getTeamDisplayName } from "../../../../utils/teamUtils";

interface StatsGridProps {
  details: MatchPrediction;
}

export const StatsGrid: React.FC<StatsGridProps> = ({ details }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  return (
    <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2} mb={3}>
      <Box gridColumn="span 2">
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>
          Probabilidades de Victoria
        </Typography>
        <Paper variant="outlined" sx={{ p: 1.5 }}>
          {details.prediction.home_win_probability + details.prediction.draw_probability + details.prediction.away_win_probability === 0 ? (
            <Typography variant="caption" color="text.secondary" display="block" textAlign="center">
              No disponible
            </Typography>
          ) : (
            <Box display="flex" justifyContent="space-between" textAlign="center">
              <Box flex={1}>
                <Typography variant="caption" display="block" color="text.secondary" mb={0.5}>1</Typography>
                <Typography variant="h6" fontWeight="bold" color="primary">
                  {(details.prediction.home_win_probability * 100).toFixed(0)}%
                </Typography>
              </Box>
              <Divider orientation="vertical" flexItem />
              <Box flex={1}>
                <Typography variant="caption" display="block" color="text.secondary" mb={0.5}>X</Typography>
                <Typography variant="h6" fontWeight="bold" color="text.secondary">
                  {(details.prediction.draw_probability * 100).toFixed(0)}%
                </Typography>
              </Box>
              <Divider orientation="vertical" flexItem />
              <Box flex={1}>
                <Typography variant="caption" display="block" color="text.secondary" mb={0.5}>2</Typography>
                <Typography variant="h6" fontWeight="bold" color="error">
                  {(details.prediction.away_win_probability * 100).toFixed(0)}%
                </Typography>
              </Box>
            </Box>
          )}
        </Paper>
      </Box>

      <Box>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>Goles Esperados</Typography>
        <Paper variant="outlined" sx={{ p: 1.5, height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", bgcolor: "rgba(255, 255, 255, 0.02)", border: "1px solid rgba(255, 255, 255, 0.05)" }}>
          <Box display="flex" justifyContent="space-between" mb={0.5}>
            <Typography variant="caption" noWrap>{isMobile ? "Local" : getTeamDisplayName(details.match.home_team)}</Typography>
            <Typography fontWeight="bold" color="primary">{details.prediction.predicted_home_goals.toFixed(1)}</Typography>
          </Box>
          <Divider sx={{ my: 0.5 }} />
          <Box display="flex" justifyContent="space-between">
            <Typography variant="caption" noWrap>{isMobile ? "Visita" : getTeamDisplayName(details.match.away_team)}</Typography>
            <Typography fontWeight="bold" color="error">{details.prediction.predicted_away_goals.toFixed(1)}</Typography>
          </Box>
        </Paper>
      </Box>

      <Box>
        <Typography variant="subtitle2" color="text.secondary" gutterBottom>Más/Menos 2.5</Typography>
        <Paper variant="outlined" sx={{ p: 1.5, height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", bgcolor: "rgba(255, 255, 255, 0.02)", border: "1px solid rgba(255, 255, 255, 0.05)" }}>
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
            <Typography variant="caption">Más</Typography>
            <Typography fontWeight="bold" color={details.prediction.over_25_probability > 0.5 ? "success.main" : "text.primary"}>
              {(details.prediction.over_25_probability * 100).toFixed(0)}%
            </Typography>
          </Box>
          <Divider sx={{ my: 0.5 }} />
          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Typography variant="caption">Menos</Typography>
            <Typography fontWeight="bold" color={details.prediction.under_25_probability > 0.5 ? "success.main" : "text.primary"}>
              {(details.prediction.under_25_probability * 100).toFixed(0)}%
            </Typography>
          </Box>
        </Paper>
      </Box>
    </Box>
  );
};

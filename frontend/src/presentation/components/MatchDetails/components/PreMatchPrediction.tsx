import React from "react";
import { Box, Typography, Paper, Divider } from "@mui/material";
import Grid from "@mui/material/Grid";
import { Prediction } from "../../../../domain/entities/prediction";

interface PreMatchPredictionProps {
  prediction: Prediction;
  isAvailable: boolean;
}

export const PreMatchPrediction: React.FC<PreMatchPredictionProps> = ({
  prediction,
  isAvailable,
}) => {
  if (!isAvailable) {
    return (
      <Box textAlign="center" py={2}>
        <Typography variant="body2" color="text.disabled">
          No hay predicción pre-partido disponible para este evento.
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      <Typography
        variant="subtitle2"
        color="primary.main"
        gutterBottom
        sx={{ display: "flex", alignItems: "center", gap: 1 }}
      >
        🎯 Predicción Pre-Partido
      </Typography>
      <Paper
        variant="outlined"
        sx={{
          p: 2,
          bgcolor: "rgba(255,255,255,0.02)",
          borderColor: "rgba(255,255,255,0.1)",
        }}
      >
        <Grid container spacing={2}>
          <Grid size={12}>
            <Box display="flex" justifyContent="space-between" mb={1}>
              <Typography variant="body2" color="text.secondary">
                Probabilidad Local
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                {(prediction.home_win_probability * 100).toFixed(0)}%
              </Typography>
            </Box>
            <Box
              sx={{
                width: "100%",
                height: 6,
                bgcolor: "rgba(255,255,255,0.1)",
                borderRadius: 1,
                overflow: "hidden",
              }}
            >
              <Box
                sx={{
                  width: `${prediction.home_win_probability * 100}%`,
                  height: "100%",
                  bgcolor: "primary.main",
                }}
              />
            </Box>
          </Grid>
          <Grid size={12}>
            <Box display="flex" justifyContent="space-between" mb={1}>
              <Typography variant="body2" color="text.secondary">
                Probabilidad Visitante
              </Typography>
              <Typography variant="body2" fontWeight="bold">
                {(prediction.away_win_probability * 100).toFixed(0)}%
              </Typography>
            </Box>
            <Box
              sx={{
                width: "100%",
                height: 6,
                bgcolor: "rgba(255,255,255,0.1)",
                borderRadius: 1,
                overflow: "hidden",
              }}
            >
              <Box
                sx={{
                  width: `${prediction.away_win_probability * 100}%`,
                  height: "100%",
                  bgcolor: "error.main",
                }}
              />
            </Box>
          </Grid>
        </Grid>
        <Divider sx={{ my: 2, borderColor: "rgba(255,255,255,0.1)" }} />
        <Box display="flex" justifyContent="space-between">
          <Box>
            <Typography variant="caption" color="text.secondary">
              Goles Esperados (Local)
            </Typography>
            <Typography variant="h6">
              {prediction.predicted_home_goals.toFixed(2)}
            </Typography>
          </Box>
          <Box textAlign="right">
            <Typography variant="caption" color="text.secondary">
              Goles Esperados (Visitante)
            </Typography>
            <Typography variant="h6">
              {prediction.predicted_away_goals.toFixed(2)}
            </Typography>
          </Box>
        </Box>
      </Paper>
    </Box>
  );
};

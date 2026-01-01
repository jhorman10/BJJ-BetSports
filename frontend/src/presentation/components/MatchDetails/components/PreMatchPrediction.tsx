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

        {prediction.suggested_picks &&
          prediction.suggested_picks.length > 0 && (
            <>
              <Divider sx={{ my: 2, borderColor: "rgba(255,255,255,0.1)" }} />
              <Typography variant="subtitle2" color="warning.main" gutterBottom>
                🚀 Picks Sugeridos
              </Typography>
              <Box display="flex" flexDirection="column" gap={1}>
                {prediction.suggested_picks.map((pick, index) => (
                  <Box
                    key={index}
                    sx={{
                      p: 1.5,
                      borderRadius: 1,
                      bgcolor: "rgba(0,0,0,0.2)",
                      border: "1px solid rgba(255,255,255,0.05)",
                    }}
                  >
                    <Box
                      display="flex"
                      justifyContent="space-between"
                      alignItems="center"
                    >
                      <Typography variant="body2" fontWeight="bold">
                        {pick.market_label}
                      </Typography>
                      {pick.suggested_stake && (
                        <Box
                          component="span"
                          sx={{
                            bgcolor: "#fbbf24",
                            color: "#000",
                            px: 1,
                            borderRadius: 1,
                            fontSize: "0.75rem",
                            fontWeight: "bold",
                          }}
                        >
                          Stake: {pick.suggested_stake}u
                        </Box>
                      )}
                    </Box>
                    <Box
                      display="flex"
                      gap={2}
                      mt={1}
                      sx={{ fontSize: "0.75rem", color: "text.secondary" }}
                    >
                      <span>Prob: {(pick.probability * 100).toFixed(0)}%</span>
                      {pick.expected_value && (
                        <span
                          style={{
                            color:
                              pick.expected_value > 0.05
                                ? "#4ade80"
                                : "inherit",
                          }}
                        >
                          EV: +{(pick.expected_value * 100).toFixed(1)}%
                        </span>
                      )}
                      {pick.odds && <span>Odds: {pick.odds.toFixed(2)}</span>}
                    </Box>
                  </Box>
                ))}
              </Box>
            </>
          )}
      </Paper>

      {prediction.real_time_odds && (
        <Paper
          variant="outlined"
          sx={{
            mt: 2,
            p: 1.5,
            bgcolor: "rgba(255,255,255,0.02)",
            borderColor: "rgba(255,255,255,0.1)",
            borderStyle: "dashed",
          }}
        >
          <Typography
            variant="caption"
            color="text.secondary"
            display="block"
            mb={1}
          >
            Cuotas en Tiempo Real (vía The Odds API):
          </Typography>
          <Box display="flex" justifyContent="space-between">
            {Object.entries(prediction.real_time_odds).map(([name, price]) => (
              <Box key={name} textAlign="center">
                <Typography variant="caption" color="text.secondary">
                  {name}
                </Typography>
                <Typography variant="body2" fontWeight="bold" color="primary">
                  {price.toFixed(2)}
                </Typography>
              </Box>
            ))}
          </Box>
        </Paper>
      )}

      {prediction.highlights_url && (
        <Box mt={2}>
          <Typography
            variant="body2"
            component="a"
            href={prediction.highlights_url}
            target="_blank"
            sx={{
              color: "primary.light",
              textDecoration: "none",
              display: "flex",
              alignItems: "center",
              gap: 1,
              "&:hover": { textDecoration: "underline" },
            }}
          >
            📺 Ver Highlights del Partido
          </Typography>
        </Box>
      )}
    </Box>
  );
};

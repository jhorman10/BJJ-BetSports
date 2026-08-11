import React, { useState } from "react";
import { Box, Typography, Paper, Divider, Chip, Button } from "@mui/material";
import Grid from "@mui/material/Grid";
import { CheckCircle, Cancel, HourglassEmpty } from "@mui/icons-material";

import { Prediction } from "../../../../domain/entities/prediction";
import { Match } from "../../../../domain/entities/match";
import { evaluatePickLive } from "../../../../utils/pickValidationUtils";

import { ScoreMatrixModal } from "./ScoreMatrixModal";

interface PreMatchPredictionProps {
  prediction: Prediction;
  isAvailable: boolean;
  match?: Match;
}

export const PreMatchPrediction: React.FC<PreMatchPredictionProps> = ({
  prediction,
  isAvailable,
  match,
}) => {
  const [matrixOpen, setMatrixOpen] = useState(false);

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
        {prediction.data_sources.includes("Rigorous ML") && (
          <Chip
            label="Rigorous ML"
            size="small"
            color="secondary"
            variant="outlined"
            sx={{
              ml: 1,
              borderColor: "#ec4899",
              color: "#ec4899",
              fontWeight: 700,
            }}
          />
        )}
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

        {/* Marcador Tentativo */}
        {prediction.score_probabilities &&
          prediction.score_probabilities.length > 0 && (
            <>
              <Divider sx={{ my: 2, borderColor: "rgba(255,255,255,0.1)" }} />
              <Box
                display="flex"
                alignItems="center"
                gap={1}
                sx={{ cursor: "pointer" }}
                onClick={() => setMatrixOpen(true)}
              >
                <Typography variant="subtitle2" color="info.main">
                  🎲 Marcador Tentativo
                </Typography>
                {prediction.score_confidence_tier && (
                  <Chip
                    label={prediction.score_confidence_tier}
                    size="small"
                    color={
                      prediction.score_confidence_tier === "Alta"
                        ? "success"
                        : prediction.score_confidence_tier === "Media"
                          ? "warning"
                          : prediction.score_confidence_tier === "Baja"
                            ? "error"
                            : "default"
                    }
                    sx={{ ml: 1 }}
                  />
                )}
                <Button
                  size="small"
                  variant="text"
                  sx={{ ml: "auto", fontSize: "0.7rem" }}
                  onClick={(e) => {
                    e.stopPropagation();
                    setMatrixOpen(true);
                  }}
                >
                  Ver matriz completa
                </Button>
              </Box>
              <Box display="flex" flexWrap="wrap" gap={1} mt={1}>
                {prediction.score_probabilities
                  .slice(0, 5)
                  .map((score, index) => (
                    <Chip
                      key={`${score.home_goals}-${score.away_goals}`}
                      label={`${score.home_goals}-${score.away_goals} ${(score.probability * 100).toFixed(1)}%`}
                      variant="outlined"
                      sx={{
                        borderColor: "rgba(255,255,255,0.2)",
                        color: "text.primary",
                        fontWeight: index === 0 ? 700 : 400,
                        bgcolor: index === 0 ? "rgba(255,255,255,0.08)" : "transparent",
                      }}
                    />
                  ))}
              </Box>
            </>
          )}

        <ScoreMatrixModal
          open={matrixOpen}
          onClose={() => setMatrixOpen(false)}
          prediction={prediction}
        />

        {prediction.suggested_picks &&
          prediction.suggested_picks.length > 0 && (
            <>
              <Divider sx={{ my: 2, borderColor: "rgba(255,255,255,0.1)" }} />
              <Typography variant="subtitle2" color="warning.main" gutterBottom>
                🚀 Picks Sugeridos
              </Typography>
              <Box display="flex" flexDirection="column" gap={1}>
                {prediction.suggested_picks.map((pick) => (
                  <Box
                    key={pick.market_type}
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
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="body2" fontWeight="bold">
                          {pick.market_label}
                        </Typography>
                        {(() => {
                          const status = evaluatePickLive(pick, match);
                          if (status === 'WON') return <CheckCircle color="success" fontSize="small" />;
                          if (status === 'LOST') return <Cancel color="error" fontSize="small" />;
                          if (status === 'PENDING') return <HourglassEmpty color="warning" fontSize="small" />;
                          return null;
                        })()}
                      </Box>
                      {pick.suggested_stake ? (
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
                      ) : null}
                    </Box>
                    <Box
                      display="flex"
                      gap={2}
                      mt={1}
                      sx={{ fontSize: "0.75rem", color: "text.secondary" }}
                    >
                      <span>Prob: {(pick.probability * 100).toFixed(0)}%</span>
                      {typeof pick.expected_value === 'number' && pick.expected_value !== 0 ? (
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
                      ) : null}
                      {pick.odds ? <span>Odds: {pick.odds.toFixed(2)}</span> : null}
                    </Box>
                  </Box>
                ))}
              </Box>
            </>
          )}
      </Paper>

      {/* Real-time odds display removed per user request */}

      {prediction.highlights_url && (
        <Box mt={2}>
          <Typography
            variant="body2"
            component="a"
            href={prediction.highlights_url}
             target="_blank"
             rel="noopener noreferrer"
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

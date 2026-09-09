import React, { useState } from "react";
import { Box, Typography, Paper, Divider, Chip, Button } from "@mui/material";

import { Prediction } from "../../../../domain/entities/prediction";
import { Match } from "../../../../domain/entities/match";

import { ScoreMatrixModal } from "./ScoreMatrixModal";
import { ProbabilityBarsPreMatch } from "./ProbabilityBarsPreMatch";
import { SuggestedPicksSection } from "./SuggestedPicksSection";

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
        Predicción Pre-Partido
        {prediction.data_sources.includes("Rigorous ML") && (
          <Chip
            label="Rigorous ML"
            size="small"
            color="secondary"
            variant="outlined"
            sx={{ ml: 1, borderColor: "#ec4899", color: "#ec4899", fontWeight: 700 }}
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
        <ProbabilityBarsPreMatch prediction={prediction} />

        {prediction.score_probabilities && prediction.score_probabilities.length > 0 && (
          <>
            <Divider sx={{ my: 2, borderColor: "rgba(255,255,255,0.1)" }} />
            <Box
              display="flex"
              alignItems="center"
              gap={1}
              sx={{ cursor: "pointer" }}
              onClick={(e) => { e.stopPropagation(); setMatrixOpen(true); }}
            >
              <Typography variant="subtitle2" color="info.main">Marcador Tentativo</Typography>
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
                onClick={(e) => { e.stopPropagation(); setMatrixOpen(true); }}
              >
                Ver matriz completa
              </Button>
            </Box>
            <Box display="flex" flexWrap="wrap" gap={1} mt={1}>
              {prediction.score_probabilities
                .filter((score) => score.probability > 0)
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

        <SuggestedPicksSection prediction={prediction} match={match} />
      </Paper>

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
            Ver Highlights del Partido
          </Typography>
        </Box>
      )}
    </Box>
  );
};

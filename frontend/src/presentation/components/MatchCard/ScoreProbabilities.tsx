import React from "react";
import { Box, Typography, Chip } from "@mui/material";

import type { MatchPrediction } from "../../../types";

interface ScoreProbabilitiesProps {
  prediction: MatchPrediction["prediction"];
  onOpenMatrix: () => void;
}

export const ScoreProbabilities: React.FC<ScoreProbabilitiesProps> = ({
  prediction,
  onOpenMatrix,
}) => {
  if (!prediction.score_probabilities || prediction.score_probabilities.length === 0) {
    return null;
  }

  return (
    <Box
      mt={2}
      p={1.5}
      sx={{
        bgcolor: "rgba(59, 130, 246, 0.08)",
        border: "1px solid rgba(59, 130, 246, 0.25)",
        borderRadius: 1,
        cursor: "pointer",
      }}
      onClick={(e) => {
        e.stopPropagation();
        onOpenMatrix();
      }}
    >
      <Box display="flex" alignItems="center" gap={1} mb={1}>
        <Typography variant="caption" color="primary.main" fontWeight={700}>
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
            sx={{ fontSize: "0.65rem", height: 20 }}
          />
        )}
        <Typography
          variant="caption"
          sx={{ ml: "auto", color: "text.secondary", fontSize: "0.65rem" }}
        >
          Ver matriz →
        </Typography>
      </Box>
      <Box display="flex" flexWrap="wrap" gap={0.8}>
        {prediction.score_probabilities.slice(0, 5).map((score, index) => (
          <Chip
            key={`${score.home_goals}-${score.away_goals}`}
            label={`${score.home_goals}-${score.away_goals} ${(score.probability * 100).toFixed(1)}%`}
            variant={index === 0 ? "filled" : "outlined"}
            size="small"
            sx={{
              borderColor: "rgba(59, 130, 246, 0.3)",
              color: index === 0 ? "#ffffff" : "text.primary",
              fontWeight: index === 0 ? 700 : 400,
              bgcolor: index === 0 ? "primary.main" : "transparent",
              fontSize: "0.7rem",
              height: 24,
              ...(index === 0 && { boxShadow: "0 0 8px rgba(59, 130, 246, 0.4)" }),
            }}
          />
        ))}
      </Box>
    </Box>
  );
};

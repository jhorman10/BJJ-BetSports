import React from "react";
import { Box, Typography, Chip } from "@mui/material";

import { MatchPrediction } from "../../../../types";
import { translateRecommendedBet, translateOverUnder } from "../../../../utils/translationUtils";

interface RecommendationBoxProps {
  details: MatchPrediction;
}

export const RecommendationBox: React.FC<RecommendationBoxProps> = ({ details }) => (
  <Box
    sx={{
      mt: 3,
      p: 2,
      background: "rgba(16, 185, 129, 0.04)",
      backdropFilter: "blur(8px)",
      border: "1px solid rgba(16, 185, 129, 0.15)",
      borderRadius: 2,
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      gap: 2,
    }}
  >
    <Typography
      variant="overline"
      sx={{ fontSize: "0.6rem", fontWeight: 800, letterSpacing: 1.5, color: "success.light", opacity: 0.8 }}
    >
      RECOMENDACIÓN
    </Typography>
    <Box sx={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 2, flexWrap: "wrap" }}>
      <Chip
        label={translateRecommendedBet(details.prediction.recommended_bet)}
        size="small"
        sx={{
          fontSize: "0.85rem",
          fontWeight: 700,
          height: 32,
          px: 1,
          background: "rgba(16, 185, 129, 0.15)",
          color: "success.light",
          border: "1px solid rgba(16, 185, 129, 0.3)",
          "& .MuiChip-label": { px: 1.5 },
        }}
      />
      <Chip
        label={translateOverUnder(details.prediction.over_under_recommendation) + " Goles"}
        size="small"
        sx={{
          fontSize: "0.85rem",
          fontWeight: 700,
          height: 32,
          px: 1,
          background: "rgba(16, 185, 129, 0.15)",
          color: "success.light",
          border: "1px solid rgba(16, 185, 129, 0.3)",
          "& .MuiChip-label": { px: 1.5 },
        }}
      />
    </Box>
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 0,
        pt: 1,
        borderTop: "1px solid rgba(16, 185, 129, 0.1)",
        width: "100%",
      }}
    >
      <Typography
        sx={{
          fontWeight: 900,
          fontSize: "2rem",
          color: "success.light",
          lineHeight: 1,
          background: "linear-gradient(180deg, #10B981 0%, #6EE7B7 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
        }}
      >
        {(details.prediction.confidence * 100).toFixed(0)}%
      </Typography>
      <Typography
        sx={{
          fontSize: "0.65rem",
          fontWeight: 800,
          textTransform: "uppercase",
          color: "success.light",
          opacity: 0.6,
          letterSpacing: 1,
        }}
      >
        Índice de Confianza
      </Typography>
    </Box>
  </Box>
);

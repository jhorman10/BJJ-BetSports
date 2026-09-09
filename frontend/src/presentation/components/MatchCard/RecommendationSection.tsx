import React from "react";
import { Box, Typography, Chip } from "@mui/material";

import type { MatchPrediction } from "../../../types";
import { translateRecommendedBet, translateOverUnder } from "../../../utils/translationUtils";

interface RecommendationSectionProps {
  prediction: MatchPrediction["prediction"];
}

export const RecommendationSection: React.FC<RecommendationSectionProps> = ({ prediction }) => (
  <Box mb={2}>
    <Typography variant="subtitle2" color="text.secondary" mb={1}>
      Recomendación
    </Typography>
    <Box
      display="flex"
      gap={1}
      flexWrap="wrap"
      sx={{
        "& .MuiChip-root": {
          maxWidth: "100%",
          height: "auto",
          "& .MuiChip-label": { whiteSpace: "normal", wordBreak: "break-word", padding: "6px 10px" },
        },
      }}
    >
      <Chip
        label={translateRecommendedBet(prediction.recommended_bet)}
        color="primary"
        sx={{
          fontWeight: 800,
          color: "#ffffff",
          bgcolor: "rgba(59, 130, 246, 0.8)",
          boxShadow: "0 0 10px rgba(59, 130, 246, 0.4)",
          border: "1px solid #3b82f6",
        }}
      />
      {(() => {
        const recPick = (prediction.suggested_picks || []).find(
          (p) => p.market_label === prediction.recommended_bet || p.market_type === prediction.recommended_bet
        );
        if (recPick?.suggested_stake) {
          return (
            <Chip
              label={`Stake: ${recPick.suggested_stake.toFixed(2)}u`}
              color="warning"
              variant="filled"
              size="small"
              sx={{ fontWeight: 700, color: "#1a1a1a", bgcolor: "#f59e0b" }}
            />
          );
        }
        return null;
      })()}
      <Chip
        label={translateOverUnder(prediction.over_under_recommendation)}
        color="secondary"
        variant="outlined"
      />
    </Box>

    <div style={{ marginBottom: 8, fontSize: "0.8rem", color: "text.secondary", marginTop: 8 }}>
      <strong>Picks Available:</strong> {prediction?.suggested_picks?.length || 0} picks
    </div>

    {prediction?.suggested_picks && prediction.suggested_picks.length > 0 && (
      <div style={{ marginTop: 4, fontSize: "0.7rem", color: "text.secondary" }}>
        {prediction.suggested_picks.slice(0, 3).map((pick) => (
          <span key={pick.market_type} style={{ marginRight: 8 }}>{pick.market_type}</span>
        ))}
      </div>
    )}
  </Box>
);

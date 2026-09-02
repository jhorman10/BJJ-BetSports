import React from "react";
import { Box, Typography, Divider } from "@mui/material";
import { CheckCircle, Cancel, HourglassEmpty } from "@mui/icons-material";

import { Prediction } from "../../../../domain/entities/prediction";
import { Match } from "../../../../domain/entities/match";
import { evaluatePickLive } from "../../../../utils/pickValidationUtils";

interface SuggestedPicksSectionProps {
  prediction: Prediction;
  match?: Match;
}

export const SuggestedPicksSection: React.FC<SuggestedPicksSectionProps> = ({ prediction, match }) => {
  if (!prediction.suggested_picks || prediction.suggested_picks.length === 0) return null;

  return (
    <>
      <Divider sx={{ my: 2, borderColor: "rgba(255,255,255,0.1)" }} />
      <Typography variant="subtitle2" color="warning.main" gutterBottom>
        Picks Sugeridos
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
            <Box display="flex" justifyContent="space-between" alignItems="center">
              <Box display="flex" alignItems="center" gap={1}>
                <Typography variant="body2" fontWeight="bold">{pick.market_label}</Typography>
                {(() => {
                  const status = evaluatePickLive(pick, match);
                  if (status === "WON") return <CheckCircle color="success" fontSize="small" />;
                  if (status === "LOST") return <Cancel color="error" fontSize="small" />;
                  if (status === "PENDING") return <HourglassEmpty color="warning" fontSize="small" />;
                  return null;
                })()}
              </Box>
              {pick.suggested_stake ? (
                <Box
                  component="span"
                  sx={{ bgcolor: "#fbbf24", color: "#000", px: 1, borderRadius: 1, fontSize: "0.75rem", fontWeight: "bold" }}
                >
                  Stake: {pick.suggested_stake}u
                </Box>
              ) : null}
            </Box>
            <Box display="flex" gap={2} mt={1} sx={{ fontSize: "0.75rem", color: "text.secondary" }}>
              <span>Prob: {(pick.probability * 100).toFixed(0)}%</span>
              {typeof pick.expected_value === "number" && pick.expected_value !== 0 ? (
                <span style={{ color: pick.expected_value > 0.05 ? "#4ade80" : "inherit" }}>
                  EV: +{(pick.expected_value * 100).toFixed(1)}%
                </span>
              ) : null}
              {pick.odds ? <span>Odds: {pick.odds.toFixed(2)}</span> : null}
            </Box>
          </Box>
        ))}
      </Box>
    </>
  );
};

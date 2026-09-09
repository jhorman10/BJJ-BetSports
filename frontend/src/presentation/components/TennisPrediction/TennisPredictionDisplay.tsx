import React from "react";
import { Box, Typography, Chip } from "@mui/material";

import { Prediction } from "../../../domain/entities";
import { Sport } from "../../../types";

export const TennisPredictionDisplay: React.FC<{
  prediction: Prediction | null;
  _sport: Sport;
}> = ({ prediction, _sport }) => {
  if (!prediction) {
    return (
      <Typography variant="h5" sx={{ p: 4, textAlign: "center", color: "text.secondary" }}>
        Predicción no disponible
      </Typography>
    );
  }
  return (
    <Box
      sx={{
        p: 3,
        borderRadius: 2,
        background: "rgba(30,41,59,0.5)",
        border: "1px solid rgba(255,255,255,0.08)",
      }}
    >
      <Typography variant="h6" sx={{ mb: 2 }}>
        {_sport === "tennis" ? "Predicción de tenis" : "Predicción"}
      </Typography>
      <Chip label={_sport} color="secondary" size="small" />
      <Typography variant="subtitle1" sx={{ mb: 1, mt: 2 }}>
        Probabilidades por Set
      </Typography>
      {prediction.setOverUnderProbabilities?.length ? (
        <Typography sx={{ mt: 1 }}>
          {prediction.setOverUnderProbabilities.map((p) => (
            <Typography variant="caption" color="text.primary" sx={{ flex: 1, textAlign: "center" }} key={p.set}>
              Set {p.set}
              <Chip label={p.over_probability > 0.5 ? "Over" : "Under"} color={p.over_probability > 0.5 ? "primary" : "secondary"} size="small" />
              <Typography variant="body2" color="text.secondary">
                {p.over_probability.toFixed(1)} / {p.under_probability.toFixed(1)}
              </Typography>
            </Typography>
          ))}
        </Typography>
      ) : null}

      <Typography variant="subtitle1" sx={{ mb: 1, mt: 2 }}>
        Probabilidades por Juego
      </Typography>
      {prediction.gameProbabilities?.length ? (
        <Typography sx={{ mt: 1 }}>
          {prediction.gameProbabilities.map((p) => (
            <Typography key={p.game} variant="caption" color="text.primary">
              Juego {p.game}
              <Chip label={p.win_probability > 0.5 ? "Ganar" : "Perder"} color={p.win_probability > 0.5 ? "primary" : "secondary"} size="small" />
              <Typography variant="body2" color="text.secondary">
                {p.win_probability.toFixed(1)}% / {p.lose_probability.toFixed(1)}%
              </Typography>
            </Typography>
          ))}
        </Typography>
      ) : null}

      <Typography variant="body2" sx={{ mt: 1 }}>
        Prob. Ganador: {prediction.home_win_probability.toFixed(1)}%
      </Typography>
      {_sport !== "soccer" && (
        <Typography color="text.secondary">(Sin empate)</Typography>
      )}
      <Typography variant="body2" color="text.secondary">
        Over 2.5: {prediction.over_25_probability.toFixed(1)}%
      </Typography>
      <Typography variant="body2" color="text.secondary">
        Under 2.5: {prediction.under_25_probability.toFixed(1)}%
      </Typography>
    </Box>
  );
};

import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Chip,
  Tooltip,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import SportsSoccer from "@mui/icons-material/SportsSoccer";

import { Prediction } from "../../../../domain/entities/prediction";

interface ScoreMatrixModalProps {
  open: boolean;
  onClose: () => void;
  prediction: Prediction | null;
}

interface ScorePoint {
  homeGoals: number;
  awayGoals: number;
  probability: number;
}

interface ScoreCell {
  home_goals: number;
  away_goals: number;
  probability: number;
  home_xg_contribution: number;
  away_xg_contribution: number;
}

const toScorePoints = (matrix: ScoreCell[][]): ScorePoint[] => {
  const points: ScorePoint[] = [];
  matrix.forEach((row) => {
    row.forEach((cell) => {
      if (cell.probability > 0) {
        points.push({
          homeGoals: cell.home_goals,
          awayGoals: cell.away_goals,
          probability: cell.probability,
        });
      }
    });
  });
  points.sort((a, b) => b.probability - a.probability);
  return points;
};

const getLevel = (probability: number, maxProb: number): number => {
  if (maxProb <= 0) return 0;
  const ratio = probability / maxProb;
  if (ratio < 0.05) return 0;
  if (ratio < 0.15) return 1;
  if (ratio < 0.35) return 2;
  if (ratio < 0.65) return 3;
  return 4;
};

const LEVEL_COLORS = [
  "rgba(255,255,255,0.03)",
  "rgba(255,255,255,0.10)",
  "rgba(255,255,255,0.20)",
  "rgba(255,255,255,0.35)",
  "rgba(255,255,255,0.55)",
];

const BellCurveVisualization: React.FC<{ points: ScorePoint[]; maxProb: number }> = ({
  points,
  maxProb,
}) => {
  const topScores = points.slice(0, 12);
  const maxProbability = maxProb || Math.max(...topScores.map((p) => p.probability), 0.001);

  return (
    <Box sx={{ position: "relative", width: "100%", height: { xs: 280, sm: 360 }, mt: 2 }}>
      <Box
        sx={{
          position: "absolute",
          left: { xs: 36, sm: 48 },
          right: { xs: 8, sm: 16 },
          top: { xs: 24, sm: 32 },
          bottom: { xs: 48, sm: 56 },
          borderLeft: "1px solid rgba(255,255,255,0.15)",
          borderBottom: "1px solid rgba(255,255,255,0.15)",
        }}
      />
      <Box
        sx={{
          position: "absolute",
          left: { xs: 36, sm: 48 },
          right: { xs: 8, sm: 16 },
          top: { xs: 24, sm: 32 },
          bottom: { xs: 48, sm: 56 },
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "center",
          gap: { xs: 0.6, sm: 1.2 },
          px: 0.5,
        }}
      >
        {topScores.map((point) => {
          const heightPercent = (point.probability / maxProbability) * 100;
          const level = getLevel(point.probability, maxProbability);
          const label = `${point.homeGoals}-${point.awayGoals}`;
          return (
            <Tooltip
              key={label}
              title={
                <Box>
                  <Typography variant="body2">{label}</Typography>
                  <Typography variant="body2">
                    Prob: {(point.probability * 100).toFixed(1)}%
                  </Typography>
                </Box>
              }
              arrow
            >
              <Box
                sx={{
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "flex-end",
                  height: "100%",
                  cursor: "pointer",
                }}
              >
                <Box
                  sx={{
                    width: "100%",
                    maxWidth: 64,
                    height: `${heightPercent}%`,
                    minHeight: 6,
                    borderRadius: 1.5,
                    background: LEVEL_COLORS[level],
                    border: "1px solid rgba(255,255,255,0.12)",
                    transition: "transform 0.2s ease",
                    "&:hover": {
                      transform: "scaleY(1.05)",
                      border: "1px solid rgba(255,255,255,0.4)",
                    },
                  }}
                />
                <Typography
                  variant="caption"
                  sx={{ mt: 0.5, color: "text.secondary", fontSize: "0.7rem" }}
                >
                  {label}
                </Typography>
              </Box>
            </Tooltip>
          );
        })}
      </Box>
      <Typography
        variant="caption"
        sx={{
          position: "absolute",
          left: 0,
          bottom: 0,
          width: "100%",
          textAlign: "center",
          color: "text.secondary",
        }}
      >
        Probabilidad estimada por marcador exacto
      </Typography>
    </Box>
  );
};

export const ScoreMatrixModal: React.FC<ScoreMatrixModalProps> = ({
  open,
  onClose,
  prediction,
}) => {
  if (!prediction) return null;

  const matrix = prediction.score_matrix;
  const accuracy = prediction.score_accuracy_history;

  const maxProb = matrix
    ? Math.max(...matrix.flatMap((row) => row.map((cell) => cell.probability)))
    : 0;

  const points = matrix ? toScorePoints(matrix) : [];
  const hasScores = points.length > 0;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      disableScrollLock
    >
      <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <SportsSoccer fontSize="small" />
        <Typography variant="h6" component="span">
          Marcador Tentativo
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
          />
        )}
        <Box flex={1} />
        <Button
          size="small"
          onClick={onClose}
          startIcon={<CloseIcon fontSize="small" />}
        >
          Cerrar
        </Button>
      </DialogTitle>
      <DialogContent dividers>
        {hasScores ? (
          <>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 2,
              }}
            >
              <Typography variant="caption" color="text.secondary">
                Distribución de probabilidad de marcador exacto
              </Typography>
              <Chip
                size="small"
                variant="outlined"
                label={`Top: ${points[0]?.homeGoals ?? 0}-${points[0]?.awayGoals ?? 0}`}
                sx={{
                  borderColor: "rgba(255,255,255,0.2)",
                  color: "text.secondary",
                }}
              />
            </Box>
            <BellCurveVisualization points={points} maxProb={maxProb} />
          </>
        ) : (
          <Typography variant="body2" color="text.disabled">
            No hay datos suficientes para calcular la distribución de marcador.
          </Typography>
        )}

        {accuracy && accuracy.total_predictions > 0 && (
          <Box mt={3} p={2} sx={{ bgcolor: "rgba(0,0,0,0.2)", borderRadius: 1 }}>
            <Typography variant="subtitle2" gutterBottom>
              Historial de Precisión del Modelo
            </Typography>
            <Box display="flex" gap={{ xs: 2, sm: 3 }} flexWrap="wrap">
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Precisión (marcador exacto)
                </Typography>
                <Typography variant="h6">
                  {(accuracy.accuracy_percentage * 100).toFixed(1)}%
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Aciertos / Total
                </Typography>
                <Typography variant="h6">
                  {accuracy.exact_score_hits} / {accuracy.total_predictions}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Liga
                </Typography>
                <Typography variant="h6">{accuracy.league_id}</Typography>
              </Box>
            </Box>
          </Box>
        )}

        {(!accuracy || accuracy.total_predictions === 0) && (
          <Box mt={3} p={2} sx={{ bgcolor: "rgba(0,0,0,0.2)", borderRadius: 1 }}>
            <Typography variant="subtitle2" gutterBottom>
              Historial de Precisión del Modelo
            </Typography>
            <Typography variant="body2" color="text.disabled">
              Datos insuficientes para mostrar precisión histórica.
            </Typography>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cerrar</Button>
      </DialogActions>
    </Dialog>
  );
};

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
  Grid,
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

const LEVEL_COLORS = [
  "rgba(255,255,255,0.03)",
  "rgba(255,255,255,0.10)",
  "rgba(255,255,255,0.20)",
  "rgba(255,255,255,0.35)",
  "rgba(255,255,255,0.55)",
];

const getLevel = (probability: number, maxProb: number): number => {
  if (maxProb <= 0) return 0;
  const ratio = probability / maxProb;
  if (ratio < 0.05) return 0;
  if (ratio < 0.15) return 1;
  if (ratio < 0.35) return 2;
  if (ratio < 0.65) return 3;
  return 4;
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

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
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
        {matrix && matrix.length > 0 ? (
          <>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1 }}>
              Matriz de probabilidades de marcador exacto (distribución de Poisson
              con xG)
            </Typography>
            <Box
              sx={{
                overflowX: "auto",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 1,
                p: 1,
              }}
            >
              <Grid container columns={7} spacing={0.5}>
                {/* Header row: away goals */}
                <Grid size={1} />
                {Array.from({ length: 6 }, (_, i) => (
                  <Grid
                    size={1}
                    key={`away-header-${i}`}
                    sx={{ textAlign: "center" }}
                  >
                    <Typography variant="caption" color="text.secondary">
                      {i}
                    </Typography>
                  </Grid>
                ))}
                {/* Matrix rows */}
                {matrix.map((row, h) => (
                  <React.Fragment key={`row-${h}`}>
                    <Grid
                      size={1}
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <Typography variant="caption" color="text.secondary">
                        {h}
                      </Typography>
                    </Grid>
                    {row.map((cell, a) => {
                      const level = getLevel(cell.probability, maxProb);
                      return (
                        <Grid size={1} key={`cell-${h}-${a}`}>
                          <Tooltip
                            title={
                              <Box>
                                <Typography variant="body2">
                                  {h}-{a}
                                </Typography>
                                <Typography variant="body2">
                                  Prob: {(cell.probability * 100).toFixed(1)}%
                                </Typography>
                                <Typography variant="body2">
                                  Local: {(cell.home_xg_contribution * 100).toFixed(0)}%
                                </Typography>
                                <Typography variant="body2">
                                  Visitante:{" "}
                                  {(cell.away_xg_contribution * 100).toFixed(0)}%
                                </Typography>
                              </Box>
                            }
                            arrow
                          >
                            <Box
                              sx={{
                                aspectRatio: "1",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                borderRadius: 1,
                                bgcolor: LEVEL_COLORS[level],
                                border: "1px solid rgba(255,255,255,0.08)",
                                cursor: "pointer",
                                "&:hover": {
                                  border: "1px solid rgba(255,255,255,0.4)",
                                },
                              }}
                            >
                              <Typography
                                variant="caption"
                                sx={{
                                  fontWeight: level >= 3 ? 700 : 400,
                                  color: level >= 3 ? "text.primary" : "text.secondary",
                                  fontSize: level >= 3 ? "0.75rem" : "0.65rem",
                                }}
                              >
                                {h}-{a}
                              </Typography>
                            </Box>
                          </Tooltip>
                        </Grid>
                      );
                    })}
                  </React.Fragment>
                ))}
              </Grid>
            </Box>
            <Box mt={2} display="flex" gap={2} flexWrap="wrap">
              <Typography variant="caption" color="text.secondary">
                Leyenda: más oscuro = mayor probabilidad
              </Typography>
            </Box>
          </>
        ) : (
          <Typography variant="body2" color="text.disabled">
            No hay datos suficientes para calcular la matriz de marcador.
          </Typography>
        )}

        {accuracy && accuracy.total_predictions > 0 && (
          <Box mt={3} p={2} sx={{ bgcolor: "rgba(0,0,0,0.2)", borderRadius: 1 }}>
            <Typography variant="subtitle2" gutterBottom>
              📊 Historial de Precisión del Modelo
            </Typography>
            <Box display="flex" gap={3} flexWrap="wrap">
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
              📊 Historial de Precisión del Modelo
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

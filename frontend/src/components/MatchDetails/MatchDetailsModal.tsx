import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Grid,
  Chip,
  Divider,
  Paper,
} from "@mui/material";
import { Warning, CompareArrows } from "@mui/icons-material";
import { MatchPrediction } from "../../types";

interface MatchDetailsModalProps {
  open: boolean;
  onClose: () => void;
  matchPrediction: MatchPrediction | null;
}

const MatchDetailsModal: React.FC<MatchDetailsModalProps> = ({
  open,
  onClose,
  matchPrediction,
}) => {
  // Use the passed data directly, no need to fetch
  const details = matchPrediction;

  if (!open) return null;

  const renderStatRow = (
    label: string,
    homeValue: number | undefined | null,
    awayValue: number | undefined | null,
    icon?: React.ReactNode
  ) => (
    <Box
      display="flex"
      justifyContent="space-between"
      alignItems="center"
      py={1}
      borderBottom="1px solid rgba(255,255,255,0.1)"
    >
      <Typography variant="body1" fontWeight="bold">
        {homeValue ?? "-"}
      </Typography>
      <Box display="flex" alignItems="center" gap={1} color="text.secondary">
        {icon}
        <Typography variant="body2">{label}</Typography>
      </Box>
      <Typography variant="body1" fontWeight="bold">
        {awayValue ?? "-"}
      </Typography>
    </Box>
  );

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle sx={{ textAlign: "center", pb: 1 }}>
        Detalles del Partido
      </DialogTitle>
      <DialogContent>
        {!details ? (
          <Box p={3} textAlign="center">
            <Typography color="text.secondary">
              No hay datos disponibles.
            </Typography>
          </Box>
        ) : (
          <Box>
            {/* Score Header */}
            <Box
              display="flex"
              justifyContent="space-between"
              alignItems="center"
              mb={3}
              p={2}
              component={Paper}
              elevation={2}
              sx={{ bgcolor: "background.paper" }}
            >
              <Box textAlign="center" flex={1}>
                <Typography variant="h6">
                  {details.match.home_team.name}
                </Typography>
              </Box>
              <Box textAlign="center" px={2}>
                <Typography variant="h4" fontWeight="bold">
                  {details.match.home_goals ?? 0} -{" "}
                  {details.match.away_goals ?? 0}
                </Typography>
                <Chip
                  label={details.match.status}
                  color={
                    details.match.status === "LIVE" ||
                    details.match.status === "1H" ||
                    details.match.status === "2H"
                      ? "error"
                      : "default"
                  }
                  size="small"
                  sx={{ mt: 1 }}
                />
              </Box>
              <Box textAlign="center" flex={1}>
                <Typography variant="h6">
                  {details.match.away_team.name}
                </Typography>
              </Box>
            </Box>

            {/* Statistics */}
            <Typography variant="subtitle1" gutterBottom sx={{ mt: 2, mb: 1 }}>
              Estadísticas
            </Typography>
            <Paper variant="outlined" sx={{ p: 2 }}>
              {renderStatRow(
                "Córners",
                details.match.home_corners,
                details.match.away_corners,
                <CompareArrows fontSize="small" />
              )}
              {renderStatRow(
                "Tarjetas Amarillas",
                details.match.home_yellow_cards,
                details.match.away_yellow_cards,
                <Warning fontSize="small" color="warning" />
              )}
              {renderStatRow(
                "Tarjetas Rojas",
                details.match.home_red_cards,
                details.match.away_red_cards,
                <Warning fontSize="small" color="error" />
              )}
            </Paper>

            {/* Prediction Info */}
            <Box mt={3}>
              <Typography variant="subtitle1" gutterBottom>
                Predicción Previa
              </Typography>
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  bgcolor: "rgba(30, 41, 59, 0.3)",
                  borderRadius: 1,
                }}
              >
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      Probabilidad Local
                    </Typography>
                    <Typography variant="body1">
                      {(details.prediction.home_win_probability * 100).toFixed(
                        0
                      )}
                      %
                    </Typography>
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      Probabilidad Visitante
                    </Typography>
                    <Typography variant="body1">
                      {(details.prediction.away_win_probability * 100).toFixed(
                        0
                      )}
                      %
                    </Typography>
                  </Grid>
                  <Grid item xs={12}>
                    <Divider sx={{ my: 1 }} />
                    <Typography variant="caption" color="text.secondary">
                      Recomendación
                    </Typography>
                    <Typography
                      variant="body1"
                      color="primary.main"
                      fontWeight="bold"
                    >
                      {details.prediction.recommended_bet}
                    </Typography>
                  </Grid>
                </Grid>
              </Paper>
            </Box>
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cerrar</Button>
      </DialogActions>
    </Dialog>
  );
};

export default MatchDetailsModal;

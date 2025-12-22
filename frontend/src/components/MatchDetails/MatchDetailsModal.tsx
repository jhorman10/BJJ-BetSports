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
import { MatchPrediction } from "../../types";
import SuggestedPicksTab from "./SuggestedPicksTab";

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
  const details = matchPrediction;

  if (!open) return null;

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
              mb={2}
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

            {/* Picks Destacados - At the top */}
            <Box mb={3}>
              <Typography
                variant="subtitle1"
                fontWeight="bold"
                gutterBottom
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 1,
                  mb: 2,
                }}
              >
                🎯 Picks Destacados
              </Typography>
              <SuggestedPicksTab matchPrediction={details} />
            </Box>

            <Divider sx={{ mb: 2 }} />

            {/* Probabilidades */}
            <Typography variant="subtitle1" gutterBottom sx={{ mb: 1 }}>
              Probabilidades
            </Typography>
            <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
              {details.prediction.confidence === 0 ? (
                <Box textAlign="center" py={2}>
                  <Typography color="warning.main" fontWeight="bold">
                    ⚠️ Datos insuficientes
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    No hay suficiente historial para calcular probabilidades
                    reales.
                  </Typography>
                </Box>
              ) : (
                <Grid container spacing={2}>
                  <Grid item xs={4} textAlign="center">
                    <Typography variant="body2" color="text.secondary">
                      Local (1)
                    </Typography>
                    <Typography variant="h5" fontWeight="bold" color="primary">
                      {(details.prediction.home_win_probability * 100).toFixed(
                        0
                      )}
                      %
                    </Typography>
                  </Grid>
                  <Grid item xs={4} textAlign="center">
                    <Typography variant="body2" color="text.secondary">
                      Empate (X)
                    </Typography>
                    <Typography
                      variant="h5"
                      fontWeight="bold"
                      color="secondary"
                    >
                      {(details.prediction.draw_probability * 100).toFixed(0)}%
                    </Typography>
                  </Grid>
                  <Grid item xs={4} textAlign="center">
                    <Typography variant="body2" color="text.secondary">
                      Visitante (2)
                    </Typography>
                    <Typography variant="h5" fontWeight="bold" color="error">
                      {(details.prediction.away_win_probability * 100).toFixed(
                        0
                      )}
                      %
                    </Typography>
                  </Grid>
                </Grid>
              )}
            </Paper>

            {/* Goles Esperados */}
            <Typography variant="subtitle1" gutterBottom sx={{ mb: 1 }}>
              Goles Esperados
            </Typography>
            <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
              <Grid container spacing={2}>
                <Grid item xs={6} textAlign="center">
                  <Typography variant="body2" color="text.secondary">
                    {details.match.home_team.name}
                  </Typography>
                  <Typography variant="h4" fontWeight="bold" color="primary">
                    {details.prediction.predicted_home_goals.toFixed(1)}
                  </Typography>
                </Grid>
                <Grid item xs={6} textAlign="center">
                  <Typography variant="body2" color="text.secondary">
                    {details.match.away_team.name}
                  </Typography>
                  <Typography variant="h4" fontWeight="bold" color="error">
                    {details.prediction.predicted_away_goals.toFixed(1)}
                  </Typography>
                </Grid>
              </Grid>
            </Paper>

            {/* More/Less than 2.5 goals */}
            <Typography variant="subtitle1" gutterBottom sx={{ mb: 1 }}>
              Más/Menos de 2.5 Goles
            </Typography>
            <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
              <Grid container spacing={2}>
                <Grid item xs={6} textAlign="center">
                  <Typography variant="body2" color="text.secondary">
                    Más de 2.5
                  </Typography>
                  <Typography
                    variant="h5"
                    fontWeight="bold"
                    color={
                      details.prediction.over_25_probability > 0.5
                        ? "success.main"
                        : "text.primary"
                    }
                  >
                    {(details.prediction.over_25_probability * 100).toFixed(0)}%
                  </Typography>
                </Grid>
                <Grid item xs={6} textAlign="center">
                  <Typography variant="body2" color="text.secondary">
                    Menos de 2.5
                  </Typography>
                  <Typography
                    variant="h5"
                    fontWeight="bold"
                    color={
                      details.prediction.under_25_probability > 0.5
                        ? "success.main"
                        : "text.primary"
                    }
                  >
                    {(details.prediction.under_25_probability * 100).toFixed(0)}
                    %
                  </Typography>
                </Grid>
              </Grid>
            </Paper>

            {/* Estadísticas Proyectadas - Corners y Tarjetas */}
            <Typography variant="subtitle1" gutterBottom sx={{ mb: 1 }}>
              Estadísticas Proyectadas
            </Typography>
            <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
              {/* Header: Team names */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                mb={2}
              >
                <Typography
                  variant="body2"
                  fontWeight="bold"
                  color="primary"
                  sx={{ flex: 1 }}
                >
                  {details.match.home_team.name}
                </Typography>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ px: 2 }}
                >
                  vs
                </Typography>
                <Typography
                  variant="body2"
                  fontWeight="bold"
                  color="error"
                  sx={{ flex: 1, textAlign: "right" }}
                >
                  {details.match.away_team.name}
                </Typography>
              </Box>

              {/* Corners */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                py={1}
                borderBottom="1px solid rgba(255,255,255,0.1)"
              >
                <Typography
                  variant="h6"
                  fontWeight="bold"
                  color="info.main"
                  sx={{ width: 40, textAlign: "center" }}
                >
                  {details.match.home_corners ?? "-"}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ flex: 1, textAlign: "center" }}
                >
                  ⚑ Córners
                </Typography>
                <Typography
                  variant="h6"
                  fontWeight="bold"
                  color="info.main"
                  sx={{ width: 40, textAlign: "center" }}
                >
                  {details.match.away_corners ?? "-"}
                </Typography>
              </Box>

              {/* Yellow Cards */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                py={1}
                borderBottom="1px solid rgba(255,255,255,0.1)"
              >
                <Typography
                  variant="h6"
                  fontWeight="bold"
                  color="warning.main"
                  sx={{ width: 40, textAlign: "center" }}
                >
                  {details.match.home_yellow_cards ?? "-"}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ flex: 1, textAlign: "center" }}
                >
                  🟨 Amarillas
                </Typography>
                <Typography
                  variant="h6"
                  fontWeight="bold"
                  color="warning.main"
                  sx={{ width: 40, textAlign: "center" }}
                >
                  {details.match.away_yellow_cards ?? "-"}
                </Typography>
              </Box>

              {/* Red Cards */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                py={1}
              >
                <Typography
                  variant="h6"
                  fontWeight="bold"
                  color="error.main"
                  sx={{ width: 40, textAlign: "center" }}
                >
                  {details.match.home_red_cards ?? "-"}
                </Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ flex: 1, textAlign: "center" }}
                >
                  🟥 Rojas
                </Typography>
                <Typography
                  variant="h6"
                  fontWeight="bold"
                  color="error.main"
                  sx={{ width: 40, textAlign: "center" }}
                >
                  {details.match.away_red_cards ?? "-"}
                </Typography>
              </Box>
            </Paper>

            {/* Recomendaciones y Confianza */}
            <Box mt={2}>
              <Typography variant="subtitle1" gutterBottom sx={{ mb: 1 }}>
                Recomendación
              </Typography>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Grid container spacing={2}>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      Apuesta Recomendada
                    </Typography>
                    <Chip
                      label={details.prediction.recommended_bet}
                      color="primary"
                      size="small"
                      sx={{ display: "block", mt: 0.5 }}
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <Typography variant="caption" color="text.secondary">
                      Over/Under
                    </Typography>
                    <Chip
                      label={details.prediction.over_under_recommendation}
                      color="secondary"
                      variant="outlined"
                      size="small"
                      sx={{ display: "block", mt: 0.5 }}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <Divider sx={{ my: 1 }} />
                    <Typography variant="caption" color="text.secondary">
                      Índice de Confianza
                    </Typography>
                    <Typography variant="body1" fontWeight="bold">
                      {(details.prediction.confidence * 100).toFixed(0)}%
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

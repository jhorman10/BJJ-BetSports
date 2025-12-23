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
  Slide,
  IconButton,
} from "@mui/material";
import { TransitionProps } from "@mui/material/transitions";
import { Close, SportsSoccer, Timer } from "@mui/icons-material";
import { useUIStore } from "../../../application/stores/useUIStore";

const LiveMatchDetailsModal: React.FC = () => {
  const { liveModalOpen, selectedLiveMatch, closeLiveMatchModal } =
    useUIStore();

  if (!liveModalOpen || !selectedLiveMatch) return null;

  const { match, prediction } = selectedLiveMatch;
  const isPredictionAvailable =
    prediction.home_win_probability > 0 || prediction.confidence > 0;

  return (
    <Dialog
      open={liveModalOpen}
      onClose={closeLiveMatchModal}
      maxWidth="sm"
      fullWidth
      TransitionComponent={Slide}
      TransitionProps={{ direction: "up" } as TransitionProps}
      PaperProps={{
        sx: {
          borderRadius: 2,
          background: "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
          color: "white",
        },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          pb: 1,
        }}
      >
        <Box display="flex" alignItems="center" gap={1}>
          <SportsSoccer color="primary" />
          <Typography variant="h6" fontWeight="bold">
            En Vivo
          </Typography>
        </Box>
        <IconButton onClick={closeLiveMatchModal} sx={{ color: "white" }}>
          <Close />
        </IconButton>
      </DialogTitle>

      <DialogContent>
        {/* Live Score Board */}
        <Paper
          elevation={3}
          sx={{
            p: 3,
            mb: 3,
            background: "rgba(255, 255, 255, 0.05)",
            backdropFilter: "blur(10px)",
            borderRadius: 2,
            border: "1px solid rgba(255, 255, 255, 0.1)",
          }}
        >
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
          >
            <Box textAlign="center" flex={1}>
              <Typography
                variant="h6"
                fontWeight="bold"
                sx={{
                  mb: 1,
                  height: 48,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {match.home_team.name}
              </Typography>
            </Box>

            <Box textAlign="center" px={2}>
              <Chip
                icon={<Timer sx={{ fontSize: "1rem !important" }} />}
                label={match.status}
                color="error"
                size="small"
                sx={{ mb: 1, fontWeight: "bold", px: 1 }}
              />
              <Typography
                variant="h3"
                fontWeight="900"
                sx={{ letterSpacing: 2 }}
              >
                {match.home_goals ?? 0} - {match.away_goals ?? 0}
              </Typography>
            </Box>

            <Box textAlign="center" flex={1}>
              <Typography
                variant="h6"
                fontWeight="bold"
                sx={{
                  mb: 1,
                  height: 48,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {match.away_team.name}
              </Typography>
            </Box>
          </Box>
        </Paper>

        {/* Live Stats Grid */}
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={6}>
            <Paper
              sx={{ p: 2, bgcolor: "rgba(0,0,0,0.2)", textAlign: "center" }}
            >
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
                mb={1}
              >
                Córners
              </Typography>
              <Box
                display="flex"
                justifyContent="center"
                gap={3}
                alignItems="center"
              >
                <Typography variant="h6" color="info.main" fontWeight="bold">
                  {match.home_corners ?? 0}
                </Typography>
                <Typography variant="h6" color="text.disabled">
                  -
                </Typography>
                <Typography variant="h6" color="info.main" fontWeight="bold">
                  {match.away_corners ?? 0}
                </Typography>
              </Box>
            </Paper>
          </Grid>
          <Grid item xs={6}>
            <Paper
              sx={{ p: 2, bgcolor: "rgba(0,0,0,0.2)", textAlign: "center" }}
            >
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
                mb={1}
              >
                Tarjetas
              </Typography>
              <Box
                display="flex"
                justifyContent="center"
                gap={3}
                alignItems="center"
              >
                <Box>
                  <Typography
                    variant="body2"
                    color="warning.main"
                    fontWeight="bold"
                    title="Amarillas"
                  >
                    🟨 {match.home_yellow_cards ?? 0}
                  </Typography>
                  <Typography
                    variant="body2"
                    color="error.main"
                    fontWeight="bold"
                    title="Rojas"
                  >
                    🟥 {match.home_red_cards ?? 0}
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary">
                  vs
                </Typography>
                <Box>
                  <Typography
                    variant="body2"
                    color="warning.main"
                    fontWeight="bold"
                    title="Amarillas"
                  >
                    🟨 {match.away_yellow_cards ?? 0}
                  </Typography>
                  <Typography
                    variant="body2"
                    color="error.main"
                    fontWeight="bold"
                    title="Rojas"
                  >
                    🟥 {match.away_red_cards ?? 0}
                  </Typography>
                </Box>
              </Box>
            </Paper>
          </Grid>
        </Grid>

        {/* Pre-match Prediction (Only if available) */}
        {isPredictionAvailable ? (
          <Box>
            <Typography
              variant="subtitle2"
              color="primary.main"
              gutterBottom
              sx={{ display: "flex", alignItems: "center", gap: 1 }}
            >
              🎯 Predicción Pre-Partido
            </Typography>
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                bgcolor: "rgba(255,255,255,0.02)",
                borderColor: "rgba(255,255,255,0.1)",
              }}
            >
              <Grid container spacing={2}>
                <Grid item xs={12}>
                  <Box display="flex" justifyContent="space-between" mb={1}>
                    <Typography variant="body2" color="text.secondary">
                      Probabilidad Local
                    </Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {(prediction.home_win_probability * 100).toFixed(0)}%
                    </Typography>
                  </Box>
                  <Box
                    sx={{
                      width: "100%",
                      height: 6,
                      bgcolor: "rgba(255,255,255,0.1)",
                      borderRadius: 1,
                      overflow: "hidden",
                    }}
                  >
                    <Box
                      sx={{
                        width: `${prediction.home_win_probability * 100}%`,
                        height: "100%",
                        bgcolor: "primary.main",
                      }}
                    />
                  </Box>
                </Grid>
                <Grid item xs={12}>
                  <Box display="flex" justifyContent="space-between" mb={1}>
                    <Typography variant="body2" color="text.secondary">
                      Probabilidad Visitante
                    </Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {(prediction.away_win_probability * 100).toFixed(0)}%
                    </Typography>
                  </Box>
                  <Box
                    sx={{
                      width: "100%",
                      height: 6,
                      bgcolor: "rgba(255,255,255,0.1)",
                      borderRadius: 1,
                      overflow: "hidden",
                    }}
                  >
                    <Box
                      sx={{
                        width: `${prediction.away_win_probability * 100}%`,
                        height: "100%",
                        bgcolor: "error.main",
                      }}
                    />
                  </Box>
                </Grid>
              </Grid>
              <Divider sx={{ my: 2, borderColor: "rgba(255,255,255,0.1)" }} />
              <Box display="flex" justifyContent="space-between">
                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Goles Esperados (Local)
                  </Typography>
                  <Typography variant="h6">
                    {prediction.predicted_home_goals.toFixed(2)}
                  </Typography>
                </Box>
                <Box textAlign="right">
                  <Typography variant="caption" color="text.secondary">
                    Goles Esperados (Visitante)
                  </Typography>
                  <Typography variant="h6">
                    {prediction.predicted_away_goals.toFixed(2)}
                  </Typography>
                </Box>
              </Box>
            </Paper>
          </Box>
        ) : (
          <Box textAlign="center" py={2}>
            <Typography variant="body2" color="text.disabled">
              No hay predicción pre-partido disponible para este evento.
            </Typography>
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ p: 2 }}>
        <Button
          onClick={closeLiveMatchModal}
          variant="contained"
          color="primary"
          fullWidth
        >
          Cerrar
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default LiveMatchDetailsModal;

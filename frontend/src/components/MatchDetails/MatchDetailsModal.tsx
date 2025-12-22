import React, { useState } from "react";
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
  Tabs,
  Tab,
} from "@mui/material";
import { Assessment, TipsAndUpdates } from "@mui/icons-material";
import { MatchPrediction } from "../../types";
import SuggestedPicksTab from "./SuggestedPicksTab";

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`match-tabpanel-${index}`}
      aria-labelledby={`match-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ pt: 2 }}>{children}</Box>}
    </div>
  );
}

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
  const [tabValue, setTabValue] = useState(0);
  const details = matchPrediction;

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

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

            {/* Tabs */}
            <Box sx={{ borderBottom: 1, borderColor: "divider", mb: 0 }}>
              <Tabs
                value={tabValue}
                onChange={handleTabChange}
                variant="fullWidth"
                sx={{
                  "& .MuiTab-root": {
                    textTransform: "none",
                    fontWeight: 600,
                  },
                }}
              >
                <Tab
                  icon={<Assessment sx={{ fontSize: 20 }} />}
                  iconPosition="start"
                  label="Detalles"
                />
                <Tab
                  icon={<TipsAndUpdates sx={{ fontSize: 20 }} />}
                  iconPosition="start"
                  label="Picks Sugeridos"
                />
              </Tabs>
            </Box>

            {/* Tab 1: Details */}
            <TabPanel value={tabValue} index={0}>
              {/* Probabilidades */}
              <Typography variant="subtitle1" gutterBottom sx={{ mb: 1 }}>
                Probabilidades
              </Typography>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Grid container spacing={2}>
                  {/* Row 1: Home / Draw / Away */}
                  <Grid item xs={4} textAlign="center">
                    <Typography variant="caption" color="text.secondary">
                      Local (1)
                    </Typography>
                    <Typography
                      variant="h5"
                      fontWeight="bold"
                      color={
                        details.prediction.home_win_probability >
                          details.prediction.away_win_probability &&
                        details.prediction.home_win_probability >
                          details.prediction.draw_probability
                          ? "success.main"
                          : "text.primary"
                      }
                    >
                      {(details.prediction.home_win_probability * 100).toFixed(
                        0
                      )}
                      %
                    </Typography>
                  </Grid>
                  <Grid item xs={4} textAlign="center">
                    <Typography variant="caption" color="text.secondary">
                      Empate (X)
                    </Typography>
                    <Typography
                      variant="h5"
                      fontWeight="bold"
                      color={
                        details.prediction.draw_probability >
                          details.prediction.home_win_probability &&
                        details.prediction.draw_probability >
                          details.prediction.away_win_probability
                          ? "warning.main"
                          : "text.primary"
                      }
                    >
                      {(details.prediction.draw_probability * 100).toFixed(0)}%
                    </Typography>
                  </Grid>
                  <Grid item xs={4} textAlign="center">
                    <Typography variant="caption" color="text.secondary">
                      Visitante (2)
                    </Typography>
                    <Typography
                      variant="h5"
                      fontWeight="bold"
                      color={
                        details.prediction.away_win_probability >
                          details.prediction.home_win_probability &&
                        details.prediction.away_win_probability >
                          details.prediction.draw_probability
                          ? "info.main"
                          : "text.primary"
                      }
                    >
                      {(details.prediction.away_win_probability * 100).toFixed(
                        0
                      )}
                      %
                    </Typography>
                  </Grid>
                </Grid>

                <Divider sx={{ my: 2 }} />

                {/* Row 2: Over/Under */}
                <Grid container spacing={2} alignItems="center">
                  <Grid item xs={6} textAlign="center">
                    <Typography variant="caption" color="text.secondary">
                      Más de 2.5 Goles
                    </Typography>
                    <Box>
                      <Chip
                        label={`${(
                          details.prediction.over_25_probability * 100
                        ).toFixed(0)}%`}
                        color={
                          details.prediction.over_25_probability > 0.5
                            ? "success"
                            : "default"
                        }
                        size="small"
                        sx={{ fontWeight: "bold" }}
                      />
                    </Box>
                  </Grid>
                  <Grid item xs={6} textAlign="center">
                    <Typography variant="caption" color="text.secondary">
                      Menos de 2.5 Goles
                    </Typography>
                    <Box>
                      <Chip
                        label={`${(
                          details.prediction.under_25_probability * 100
                        ).toFixed(0)}%`}
                        color={
                          details.prediction.under_25_probability > 0.5
                            ? "error"
                            : "default"
                        }
                        size="small"
                        sx={{ fontWeight: "bold" }}
                      />
                    </Box>
                  </Grid>
                </Grid>

                <Divider sx={{ my: 2 }} />

                {/* Row 3: Expected Goals */}
                <Grid container spacing={2}>
                  <Grid item xs={6} textAlign="center">
                    <Typography variant="caption" color="text.secondary">
                      Goles Esperados Local
                    </Typography>
                    <Typography variant="h6" color="primary.main">
                      {details.prediction.predicted_home_goals.toFixed(1)}
                    </Typography>
                  </Grid>
                  <Grid item xs={6} textAlign="center">
                    <Typography variant="caption" color="text.secondary">
                      Goles Esperados Visitante
                    </Typography>
                    <Typography variant="h6" color="primary.main">
                      {details.prediction.predicted_away_goals.toFixed(1)}
                    </Typography>
                  </Grid>
                </Grid>
              </Paper>

              {/* Proyección de Eventos */}
              <Typography
                variant="subtitle1"
                gutterBottom
                sx={{ mt: 3, mb: 1 }}
              >
                Proyección de Eventos
              </Typography>
              <Paper variant="outlined" sx={{ p: 2 }}>
                <Grid container spacing={2}>
                  {/* Corners Row */}
                  <Grid item xs={4} textAlign="center">
                    <Typography variant="h6" fontWeight="bold">
                      {details.match.home_corners ?? "-"}
                    </Typography>
                  </Grid>
                  <Grid item xs={4} textAlign="center">
                    <Typography variant="body2" color="text.secondary">
                      ⚑ Córners
                    </Typography>
                  </Grid>
                  <Grid item xs={4} textAlign="center">
                    <Typography variant="h6" fontWeight="bold">
                      {details.match.away_corners ?? "-"}
                    </Typography>
                  </Grid>

                  {/* Yellow Cards Row */}
                  <Grid item xs={4} textAlign="center">
                    <Typography
                      variant="h6"
                      fontWeight="bold"
                      color="warning.main"
                    >
                      {details.match.home_yellow_cards ?? "-"}
                    </Typography>
                  </Grid>
                  <Grid item xs={4} textAlign="center">
                    <Typography variant="body2" color="text.secondary">
                      🟨 Amarillas
                    </Typography>
                  </Grid>
                  <Grid item xs={4} textAlign="center">
                    <Typography
                      variant="h6"
                      fontWeight="bold"
                      color="warning.main"
                    >
                      {details.match.away_yellow_cards ?? "-"}
                    </Typography>
                  </Grid>

                  {/* Red Cards Row */}
                  <Grid item xs={4} textAlign="center">
                    <Typography
                      variant="h6"
                      fontWeight="bold"
                      color="error.main"
                    >
                      {details.match.home_red_cards ?? "-"}
                    </Typography>
                  </Grid>
                  <Grid item xs={4} textAlign="center">
                    <Typography variant="body2" color="text.secondary">
                      🟥 Rojas
                    </Typography>
                  </Grid>
                  <Grid item xs={4} textAlign="center">
                    <Typography
                      variant="h6"
                      fontWeight="bold"
                      color="error.main"
                    >
                      {details.match.away_red_cards ?? "-"}
                    </Typography>
                  </Grid>
                </Grid>
              </Paper>

              {/* Recommendation Section */}
              <Box mt={3}>
                <Typography variant="subtitle1" gutterBottom>
                  Recomendación
                </Typography>
                <Paper
                  elevation={0}
                  sx={{
                    p: 2,
                    bgcolor: "rgba(30, 41, 59, 0.3)",
                    borderRadius: 1,
                  }}
                >
                  <Grid container spacing={2} alignItems="center">
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Resultado
                      </Typography>
                      <Typography
                        variant="body1"
                        color="primary.main"
                        fontWeight="bold"
                      >
                        {details.prediction.recommended_bet}
                      </Typography>
                    </Grid>
                    <Grid item xs={6}>
                      <Typography variant="caption" color="text.secondary">
                        Goles
                      </Typography>
                      <Typography
                        variant="body1"
                        color="secondary.main"
                        fontWeight="bold"
                      >
                        {details.prediction.over_under_recommendation}
                      </Typography>
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
            </TabPanel>

            {/* Tab 2: Suggested Picks */}
            <TabPanel value={tabValue} index={1}>
              <SuggestedPicksTab matchId={details.match.id} />
            </TabPanel>
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

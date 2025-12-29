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
  Divider,
  Paper,
  Slide,
  useTheme,
  useMediaQuery,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import { TransitionProps } from "@mui/material/transitions";
import { MatchPrediction } from "../../../types";
import SuggestedPicksTab from "./SuggestedPicksTab";
import {
  translateMatchStatus,
  translateRecommendedBet,
  translateOverUnder,
} from "../../../utils/translationUtils";

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
  const [picksCount, setPicksCount] = React.useState<number | null>(null);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const details = matchPrediction;

  if (!open) return null;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      TransitionComponent={Slide}
      TransitionProps={{ direction: "up" } as TransitionProps}
      PaperProps={{
        sx: {
          width: { xs: "95%", sm: "100%" },
          margin: { xs: 1, sm: 2 },
          maxHeight: { xs: "90vh", sm: "calc(100% - 64px)" },
          borderRadius: 2,
        },
      }}
    >
      <DialogTitle sx={{ textAlign: "center", pb: 1, pt: 2 }}>
        <Typography component="span" variant="h6" fontWeight="bold">
          Detalles del Partido
        </Typography>
      </DialogTitle>

      <DialogContent
        sx={{ px: { xs: 1.5, sm: 3 }, pb: 3, overflowX: "hidden" }}
      >
        {!details ? (
          <Box p={3} textAlign="center">
            <Typography color="text.secondary">
              No hay datos disponibles.
            </Typography>
          </Box>
        ) : (
          <Box>
            {/* Score Header - Responsive Design */}
            <Paper
              elevation={0}
              variant="outlined"
              sx={{
                mb: 3,
                p: { xs: 1.5, sm: 2 },
                bgcolor: "background.paper",
                borderRadius: 2,
                mt: 1,
              }}
            >
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
                gap={1}
              >
                {/* Home Team */}
                <Box
                  textAlign="center"
                  flex={1}
                  display="flex"
                  flexDirection="column"
                  alignItems="center"
                >
                  {details.match.home_team.logo_url && (
                    <Box
                      component="img"
                      src={details.match.home_team.logo_url}
                      alt={details.match.home_team.name}
                      sx={{
                        width: 40,
                        height: 40,
                        mb: 1,
                        objectFit: "contain",
                      }}
                    />
                  )}
                  <Typography
                    variant={isMobile ? "body2" : "subtitle1"}
                    lineHeight={1.2}
                    fontWeight="bold"
                  >
                    {details.match.home_team.name}
                  </Typography>
                </Box>

                {/* Score & Status */}
                <Box textAlign="center" px={1} minWidth={80}>
                  <Box
                    bgcolor="rgba(0,0,0,0.4)"
                    borderRadius={2}
                    px={2}
                    py={0.5}
                    mb={1}
                    display="inline-block"
                  >
                    <Typography variant="h5" fontWeight="900" letterSpacing={1}>
                      {details.match.home_goals ?? 0}-
                      {details.match.away_goals ?? 0}
                    </Typography>
                  </Box>
                  <Box display="flex" justifyContent="center">
                    <Chip
                      label={translateMatchStatus(details.match.status)}
                      color={
                        ["LIVE", "1H", "2H", "HT"].includes(
                          details.match.status
                        )
                          ? "error"
                          : "default"
                      }
                      size="small"
                      sx={{
                        fontWeight: "bold",
                        fontSize: "0.7rem",
                        height: 20,
                      }}
                    />
                  </Box>
                </Box>

                {/* Away Team */}
                <Box
                  textAlign="center"
                  flex={1}
                  display="flex"
                  flexDirection="column"
                  alignItems="center"
                >
                  {details.match.away_team.logo_url && (
                    <Box
                      component="img"
                      src={details.match.away_team.logo_url}
                      alt={details.match.away_team.name}
                      sx={{
                        width: 40,
                        height: 40,
                        mb: 1,
                        objectFit: "contain",
                      }}
                    />
                  )}
                  <Typography
                    variant={isMobile ? "body2" : "subtitle1"}
                    lineHeight={1.2}
                    fontWeight="bold"
                  >
                    {details.match.away_team.name}
                  </Typography>
                </Box>
              </Box>
            </Paper>

            {/* Picks Destacados */}
            <Box mb={3}>
              <Box
                display="flex"
                alignItems="center"
                justifyContent="space-between"
                mb={1.5}
              >
                <Typography
                  variant="subtitle1"
                  fontWeight="bold"
                  sx={{ display: "flex", alignItems: "center", gap: 1 }}
                >
                  🎯 Picks Destacados
                </Typography>
                {picksCount !== null && picksCount > 0 && (
                  <Chip
                    label={`${picksCount} picks`}
                    size="small"
                    sx={{
                      fontWeight: "bold",
                      bgcolor: "rgba(255, 255, 255, 0.1)",
                      color: "rgba(255, 255, 255, 0.9)",
                      border: "1px solid rgba(255, 255, 255, 0.2)",
                    }}
                  />
                )}
              </Box>
              <SuggestedPicksTab
                matchPrediction={details}
                onPicksCount={setPicksCount}
              />
            </Box>

            <Divider sx={{ mb: 2.5 }} />

            {/* Stats Grid - Using CSS Grid for better control than MUI Grid */}
            <Box display="grid" gridTemplateColumns="1fr 1fr" gap={2} mb={3}>
              {/* 1. Probabilidades */}
              <Box gridColumn="span 2">
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                >
                  Probabilidades de Victoria
                </Typography>
                <Paper variant="outlined" sx={{ p: 1.5 }}>
                  {details.prediction.home_win_probability +
                    details.prediction.draw_probability +
                    details.prediction.away_win_probability ===
                  0 ? (
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      display="block"
                      textAlign="center"
                    >
                      No disponible
                    </Typography>
                  ) : (
                    <Box
                      display="flex"
                      justifyContent="space-between"
                      textAlign="center"
                    >
                      <Box flex={1}>
                        <Typography
                          variant="caption"
                          display="block"
                          color="text.secondary"
                          mb={0.5}
                        >
                          1
                        </Typography>
                        <Typography
                          variant="h6"
                          fontWeight="bold"
                          color="primary"
                        >
                          {(
                            details.prediction.home_win_probability * 100
                          ).toFixed(0)}
                          %
                        </Typography>
                      </Box>
                      <Divider orientation="vertical" flexItem />
                      <Box flex={1}>
                        <Typography
                          variant="caption"
                          display="block"
                          color="text.secondary"
                          mb={0.5}
                        >
                          X
                        </Typography>
                        <Typography
                          variant="h6"
                          fontWeight="bold"
                          color="text.secondary"
                        >
                          {(details.prediction.draw_probability * 100).toFixed(
                            0
                          )}
                          %
                        </Typography>
                      </Box>
                      <Divider orientation="vertical" flexItem />
                      <Box flex={1}>
                        <Typography
                          variant="caption"
                          display="block"
                          color="text.secondary"
                          mb={0.5}
                        >
                          2
                        </Typography>
                        <Typography
                          variant="h6"
                          fontWeight="bold"
                          color="error"
                        >
                          {(
                            details.prediction.away_win_probability * 100
                          ).toFixed(0)}
                          %
                        </Typography>
                      </Box>
                    </Box>
                  )}
                </Paper>
              </Box>

              {/* 2. Goles Esperados */}
              <Box>
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                >
                  Goles Esperados
                </Typography>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 1.5,
                    height: "100%",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "center",
                  }}
                >
                  <Box display="flex" justifyContent="space-between" mb={0.5}>
                    <Typography variant="caption" noWrap>
                      {isMobile ? "Local" : details.match.home_team.name}
                    </Typography>
                    <Typography fontWeight="bold" color="primary">
                      {details.prediction.predicted_home_goals.toFixed(1)}
                    </Typography>
                  </Box>
                  <Divider sx={{ my: 0.5 }} />
                  <Box display="flex" justifyContent="space-between">
                    <Typography variant="caption" noWrap>
                      {isMobile ? "Visita" : details.match.away_team.name}
                    </Typography>
                    <Typography fontWeight="bold" color="error">
                      {details.prediction.predicted_away_goals.toFixed(1)}
                    </Typography>
                  </Box>
                </Paper>
              </Box>

              {/* 3. Mas/Menos 2.5 */}
              <Box>
                <Typography
                  variant="subtitle2"
                  color="text.secondary"
                  gutterBottom
                >
                  Más/Menos 2.5
                </Typography>
                <Paper
                  variant="outlined"
                  sx={{
                    p: 1.5,
                    height: "100%",
                    display: "flex",
                    flexDirection: "column",
                    justifyContent: "center",
                  }}
                >
                  <Box
                    display="flex"
                    justifyContent="space-between"
                    alignItems="center"
                    mb={0.5}
                  >
                    <Typography variant="caption">Más</Typography>
                    <Typography
                      fontWeight="bold"
                      color={
                        details.prediction.over_25_probability > 0.5
                          ? "success.main"
                          : "text.primary"
                      }
                    >
                      {(details.prediction.over_25_probability * 100).toFixed(
                        0
                      )}
                      %
                    </Typography>
                  </Box>
                  <Divider sx={{ my: 0.5 }} />
                  <Box
                    display="flex"
                    justifyContent="space-between"
                    alignItems="center"
                  >
                    <Typography variant="caption">Menos</Typography>
                    <Typography
                      fontWeight="bold"
                      color={
                        details.prediction.under_25_probability > 0.5
                          ? "success.main"
                          : "text.primary"
                      }
                    >
                      {(details.prediction.under_25_probability * 100).toFixed(
                        0
                      )}
                      %
                    </Typography>
                  </Box>
                </Paper>
              </Box>
            </Box>

            {/* Estadísticas Proyectadas */}
            <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
              Estadísticas Proyectadas
            </Typography>
            <Paper variant="outlined" sx={{ p: 0, mb: 3, overflow: "hidden" }}>
              <Box
                bgcolor="rgba(255,255,255,0.03)"
                p={1.5}
                display="flex"
                justifyContent="space-between"
              >
                <Typography variant="caption" fontWeight="bold">
                  {details.match.home_team.name}
                </Typography>
                <Typography variant="caption" fontWeight="bold">
                  {details.match.away_team.name}
                </Typography>
              </Box>

              {/* Rows */}
              {[
                {
                  label: "Córners",
                  home: details.match.home_corners,
                  away: details.match.away_corners,
                  icon: "⚑",
                },
                {
                  label: "Amarillas",
                  home: details.match.home_yellow_cards,
                  away: details.match.away_yellow_cards,
                  icon: "🟨",
                },
                {
                  label: "Rojas",
                  home: details.match.home_red_cards,
                  away: details.match.away_red_cards,
                  icon: "🟥",
                },
              ].map((row, i) => (
                <Box
                  key={row.label}
                  display="flex"
                  justifyContent="space-between"
                  alignItems="center"
                  p={1.5}
                  borderTop={
                    i > 0 ? "1px solid rgba(255,255,255,0.05)" : "none"
                  }
                >
                  <Box width={40} textAlign="center">
                    <Typography fontWeight="bold">{row.home ?? "-"}</Typography>
                  </Box>
                  <Box
                    display="flex"
                    flexDirection="column"
                    alignItems="center"
                  >
                    <Typography variant="caption" color="text.secondary">
                      {row.icon} {row.label}
                    </Typography>
                  </Box>
                  <Box width={40} textAlign="center">
                    <Typography fontWeight="bold">{row.away ?? "-"}</Typography>
                  </Box>
                </Box>
              ))}
            </Paper>

            {/* Recomendación Final */}
            <Paper
              elevation={0}
              sx={{
                p: 2,
                bgcolor: "rgba(16, 185, 129, 0.1)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                borderRadius: 2,
              }}
            >
              <Grid container spacing={3}>
                {/* Main Recommendation - Full width, prominent */}
                <Grid size={{ xs: 12 }}>
                  <Box
                    sx={{
                      p: 2.5,
                      borderRadius: 2,
                      bgcolor: "success.dark",
                      border: "2px solid",
                      borderColor: "success.main",
                    }}
                  >
                    <Typography
                      variant="overline"
                      sx={{
                        fontSize: "0.7rem",
                        fontWeight: 600,
                        letterSpacing: 1.5,
                        color: "success.light",
                        opacity: 0.8,
                      }}
                    >
                      🎯 RECOMENDACIÓN PRINCIPAL
                    </Typography>

                    <Box
                      display="flex"
                      alignItems="center"
                      justifyContent="space-between"
                      mt={1.5}
                      flexWrap="wrap"
                      gap={2}
                    >
                      {/* Bet Type - Large and clear */}
                      <Chip
                        label={translateRecommendedBet(
                          details.prediction.recommended_bet
                        )}
                        color="success"
                        sx={{
                          fontSize: "1.1rem",
                          fontWeight: "bold",
                          height: 48,
                          px: 2,
                          "& .MuiChip-label": {
                            px: 2,
                          },
                        }}
                      />

                      {/* Confidence - Prominent display */}
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "baseline",
                          gap: 1,
                        }}
                      >
                        <Typography
                          variant="h2"
                          sx={{
                            fontWeight: 900,
                            color: "success.light",
                            lineHeight: 1,
                            fontSize: { xs: "2.5rem", sm: "3rem" },
                          }}
                        >
                          {(details.prediction.confidence * 100).toFixed(0)}%
                        </Typography>
                        <Typography
                          variant="caption"
                          sx={{
                            color: "success.light",
                            opacity: 0.7,
                            fontWeight: 500,
                          }}
                        >
                          confianza
                        </Typography>
                      </Box>
                    </Box>

                    {/* Over/Under - Clear secondary info */}
                    <Box mt={2} display="flex" alignItems="center" gap={1}>
                      <Typography
                        variant="caption"
                        sx={{
                          color: "success.light",
                          opacity: 0.7,
                          fontWeight: 500,
                        }}
                      >
                        Goles:
                      </Typography>
                      <Chip
                        label={translateOverUnder(
                          details.prediction.over_under_recommendation
                        )}
                        size="small"
                        variant="outlined"
                        color="success"
                        sx={{
                          fontWeight: 600,
                          borderWidth: 2,
                        }}
                      />
                    </Box>
                  </Box>
                </Grid>
              </Grid>
            </Paper>
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={onClose} variant="outlined" color="inherit">
          Cerrar
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default MatchDetailsModal;

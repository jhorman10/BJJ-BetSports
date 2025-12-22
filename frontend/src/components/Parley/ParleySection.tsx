import React, { useMemo } from "react";
import {
  Box,
  Paper,
  Typography,
  Grid,
  Chip,
  Button,
  Divider,
  CircularProgress,
  Card,
  CardContent,
  Stack,
} from "@mui/material";
import {
  LocalActivity,
  TrendingUp,
  AttachMoney,
  CheckCircle,
  SportsSoccer,
} from "@mui/icons-material";
import { MatchPrediction } from "../../types";

interface ParleySectionProps {
  predictions: MatchPrediction[];
  loading: boolean;
}

const ParleySection: React.FC<ParleySectionProps> = ({
  predictions,
  loading,
}) => {
  // Calculate top picks for the parley
  const parleyPicks = useMemo(() => {
    if (!predictions || predictions.length === 0) return [];

    // Filter for reasonably high confidence and sort by confidence desc
    return [...predictions]
      .filter((p) => p.prediction.confidence > 60)
      .sort((a, b) => b.prediction.confidence - a.prediction.confidence)
      .slice(0, 3); // Top 3 picks
  }, [predictions]);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 4 }}>
        <CircularProgress size={24} sx={{ mr: 2 }} />
        <Typography color="text.secondary">
          Analizando mejores combinaciones...
        </Typography>
      </Box>
    );
  }

  if (parleyPicks.length < 2) {
    return null;
  }

  // Calculate combined odds (mock calculation if odds missing, or real if available)
  // Since prediction doesn't have explicit selected market odds in the interface shown earlier
  // (it has home_odds, draw_odds, away_odds in match, but recommendation is safe bet)
  // We'll just display the picks.

  return (
    <Paper
      elevation={0}
      sx={{
        p: 3,
        mb: 4,
        background: "rgba(30, 41, 59, 0.7)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(99, 102, 241, 0.3)",
        borderRadius: 3,
        position: "relative",
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "4px",
          background: "linear-gradient(90deg, #6366f1, #8b5cf6, #ec4899)",
        }}
      />

      <Grid container spacing={3} alignItems="center">
        <Grid item xs={12} md={4}>
          <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
            <LocalActivity sx={{ color: "#8b5cf6", fontSize: 32, mr: 2 }} />
            <Box>
              <Typography
                variant="h5"
                fontWeight="bold"
                sx={{ color: "white" }}
              >
                Parley Sugerido
              </Typography>
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                Combinación de alta probabilidad
              </Typography>
            </Box>
          </Box>

          <Box sx={{ mt: 2, display: "flex", gap: 1 }}>
            <Chip
              icon={<TrendingUp sx={{ fontSize: "16px !important" }} />}
              label="Alta Confianza"
              size="small"
              color="success"
              variant="outlined"
            />
            <Chip
              label={`${parleyPicks.length} Selecciones`}
              size="small"
              sx={{
                borderColor: "rgba(255,255,255,0.1)",
                color: "text.secondary",
              }}
              variant="outlined"
            />
          </Box>
        </Grid>

        <Grid item xs={12} md={8}>
          <Grid container spacing={2}>
            {parleyPicks.map((pick) => (
              <Grid item xs={12} sm={4} key={pick.match.id}>
                <Card
                  sx={{
                    background: "rgba(255, 255, 255, 0.03)",
                    border: "1px solid rgba(255, 255, 255, 0.05)",
                    height: "100%",
                  }}
                >
                  <CardContent sx={{ p: 2, "&:last-child": { p: 2 } }}>
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        mb: 1,
                      }}
                    >
                      <Typography
                        variant="caption"
                        sx={{ color: "#6366f1", fontWeight: "bold" }}
                      >
                        {pick.match.league.country}
                      </Typography>
                      <Typography
                        variant="caption"
                        sx={{ color: "text.secondary" }}
                      >
                        {new Date(pick.match.match_date).toLocaleTimeString(
                          [],
                          { hour: "2-digit", minute: "2-digit" }
                        )}
                      </Typography>
                    </Box>

                    <Typography
                      variant="subtitle2"
                      sx={{
                        color: "white",
                        mb: 1,
                        minHeight: 40,
                        lineHeight: 1.2,
                      }}
                    >
                      {pick.match.home_team.name} vs {pick.match.away_team.name}
                    </Typography>

                    <Divider
                      sx={{ my: 1, borderColor: "rgba(255,255,255,0.05)" }}
                    />

                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <Typography
                        variant="body2"
                        sx={{ color: "#10b981", fontWeight: "bold" }}
                      >
                        {pick.prediction.recommended_bet}
                      </Typography>
                      <Chip
                        label={`${pick.prediction.confidence}%`}
                        size="small"
                        sx={{
                          height: 20,
                          fontSize: "0.7rem",
                          bgcolor: "rgba(16, 185, 129, 0.1)",
                          color: "#10b981",
                          border: "none",
                        }}
                      />
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Grid>
      </Grid>
    </Paper>
  );
};

export default ParleySection;

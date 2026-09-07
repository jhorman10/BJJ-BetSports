import React, { useState } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  Grid,
  Divider,
} from "@mui/material";
import {
  TrendingUp,
  EmojiEvents,
  Star,
  SportsMma,
  CheckCircle,
} from "@mui/icons-material";
import { TennisUpcomingMatch } from "../../../types";
import TennisMatchDetailsModal from "./TennisMatchDetailsModal";

interface TennisMatchCardProps {
  match: TennisUpcomingMatch;
}

const SURFACE_COLORS: Record<string, string> = {
  Hard: "#3b82f6",
  Clay: "#f97316",
  Grass: "#22c55e",
  "Hard (Indoor)": "#6366f1",
  Carpet: "#a855f7",
};

const TennisMatchCard: React.FC<TennisMatchCardProps> = ({ match }) => {
  const [modalOpen, setModalOpen] = useState(false);
  const { prediction } = match;
  const p1Win = prediction.p1_win_prob * 100;
  const p2Win = prediction.p2_win_prob * 100;
  const isP1Winner = prediction.predicted_winner === "Player 1";
  const surfaceColor = SURFACE_COLORS[match.surface] || "#6366f1";
  const confidencePercent = prediction.confidence * 100;

  const getConfidenceColor = () => {
    if (confidencePercent >= 70) return "#10b981";
    if (confidencePercent >= 40) return "#f59e0b";
    return "#ef4444";
  };

  const getWinRateColor = (rate: number) => {
    if (rate >= 0.7) return "#10b981";
    if (rate >= 0.5) return "#f59e0b";
    return "#ef4444";
  };

  return (
    <>
      <Card
        onClick={() => setModalOpen(true)}
        sx={{
          background: "linear-gradient(165deg, rgba(20,25,35,0.85) 0%, rgba(15,20,30,0.95) 100%)",
          border: "1px solid rgba(255,255,255,0.08)",
          borderRadius: "20px",
          transition: "all 0.3s ease",
          cursor: "pointer",
          "&:hover": {
            transform: "translateY(-4px)",
            boxShadow: "0 12px 40px rgba(0,0,0,0.3)",
            borderColor: "rgba(99,102,241,0.3)",
          },
        }}
      >
        <CardContent sx={{ p: 2.5 }}>
          {/* Header: Tournament + Surface + Round */}
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Box display="flex" alignItems="center" gap={1}>
              <EmojiEvents sx={{ color: "#f59e0b", fontSize: 18 }} />
              <Typography variant="subtitle2" fontWeight={600} color="rgba(255,255,255,0.9)">
                {match.tournament}
              </Typography>
            </Box>
            <Box display="flex" gap={0.5}>
              <Chip
                label={match.surface}
                size="small"
                sx={{
                  bgcolor: surfaceColor,
                  color: "white",
                  fontWeight: 600,
                  fontSize: "0.7rem",
                  height: 22,
                }}
              />
              <Chip
                label={match.round}
                size="small"
                variant="outlined"
                sx={{
                  borderColor: "rgba(255,255,255,0.2)",
                  color: "rgba(255,255,255,0.7)",
                  fontSize: "0.7rem",
                  height: 22,
                }}
              />
            </Box>
          </Box>

          {/* Players */}
          <Grid container spacing={1} alignItems="center" mb={2}>
            {/* Player 1 */}
            <Grid size={{ xs: 5 }}>
              <Box
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  bgcolor: isP1Winner ? "rgba(99,102,241,0.12)" : "transparent",
                  border: isP1Winner ? "1px solid rgba(99,102,241,0.25)" : "1px solid transparent",
                }}
              >
                <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
                  {isP1Winner && <TrendingUp sx={{ color: "#6366f1", fontSize: 16 }} />}
                  <Typography
                    variant="body1"
                    fontWeight={isP1Winner ? 700 : 500}
                    sx={{ color: isP1Winner ? "#a5b4fc" : "rgba(255,255,255,0.9)" }}
                  >
                    {match.player1.name}
                  </Typography>
                </Box>
                <Box display="flex" gap={0.5} flexWrap="wrap">
                  {match.player1.rank && (
                    <Chip
                      label={`#${match.player1.rank}`}
                      size="small"
                      sx={{
                        bgcolor: "rgba(255,255,255,0.08)",
                        color: "rgba(255,255,255,0.7)",
                        fontSize: "0.65rem",
                        height: 18,
                      }}
                    />
                  )}
                  {match.player1.seed && (
                    <Chip
                      label={`S${match.player1.seed}`}
                      size="small"
                      sx={{
                        bgcolor: "rgba(245,158,11,0.15)",
                        color: "#f59e0b",
                        fontSize: "0.65rem",
                        height: 18,
                      }}
                    />
                  )}
                </Box>
              </Box>
            </Grid>

            {/* VS */}
            <Grid size={{ xs: 2 }}>
              <Box textAlign="center">
                <Typography
                  variant="caption"
                  fontWeight={700}
                  sx={{ color: "rgba(255,255,255,0.3)" }}
                >
                  VS
                </Typography>
              </Box>
            </Grid>

            {/* Player 2 */}
            <Grid size={{ xs: 5 }}>
              <Box
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  bgcolor: !isP1Winner ? "rgba(16,185,129,0.12)" : "transparent",
                  border: !isP1Winner ? "1px solid rgba(16,185,129,0.25)" : "1px solid transparent",
                }}
                textAlign="right"
              >
                <Box display="flex" alignItems="center" justifyContent="flex-end" gap={0.5} mb={0.5}>
                  <Typography
                    variant="body1"
                    fontWeight={!isP1Winner ? 700 : 500}
                    sx={{ color: !isP1Winner ? "#6ee7b7" : "rgba(255,255,255,0.9)" }}
                  >
                    {match.player2.name}
                  </Typography>
                  {!isP1Winner && <TrendingUp sx={{ color: "#10b981", fontSize: 16 }} />}
                </Box>
                <Box display="flex" gap={0.5} justifyContent="flex-end" flexWrap="wrap">
                  {match.player2.seed && (
                    <Chip
                      label={`S${match.player2.seed}`}
                      size="small"
                      sx={{
                        bgcolor: "rgba(245,158,11,0.15)",
                        color: "#f59e0b",
                        fontSize: "0.65rem",
                        height: 18,
                      }}
                    />
                  )}
                  {match.player2.rank && (
                    <Chip
                      label={`#${match.player2.rank}`}
                      size="small"
                      sx={{
                        bgcolor: "rgba(255,255,255,0.08)",
                        color: "rgba(255,255,255,0.7)",
                        fontSize: "0.65rem",
                        height: 18,
                      }}
                    />
                  )}
                </Box>
              </Box>
            </Grid>
          </Grid>

          {/* Probability Bar */}
          <Box mb={2}>
            <Box display="flex" justifyContent="space-between" mb={0.5}>
              <Typography
                variant="caption"
                fontWeight={600}
                sx={{ color: isP1Winner ? "#a5b4fc" : "rgba(255,255,255,0.5)" }}
              >
                {p1Win.toFixed(0)}%
              </Typography>
              <Typography
                variant="caption"
                fontWeight={600}
                sx={{ color: !isP1Winner ? "#6ee7b7" : "rgba(255,255,255,0.5)" }}
              >
                {p2Win.toFixed(0)}%
              </Typography>
            </Box>
            <Box
              sx={{
                height: 6,
                borderRadius: 3,
                bgcolor: "rgba(255,255,255,0.06)",
                overflow: "hidden",
                display: "flex",
              }}
            >
              <Box
                sx={{
                  width: `${p1Win}%`,
                  background: isP1Winner
                    ? "linear-gradient(90deg, #6366f1, #818cf8)"
                    : "rgba(99,102,241,0.4)",
                  borderRadius: "3px 0 0 3px",
                  transition: "width 0.6s ease",
                }}
              />
              <Box
                sx={{
                  width: `${p2Win}%`,
                  background: !isP1Winner
                    ? "linear-gradient(90deg, #10b981, #34d399)"
                    : "rgba(16,185,129,0.4)",
                  borderRadius: "0 3px 3px 0",
                  transition: "width 0.6s ease",
                }}
              />
            </Box>
          </Box>

          <Divider sx={{ borderColor: "rgba(255,255,255,0.06)", mb: 2 }} />

          {/* Context Stats Grid */}
          <Grid container spacing={1.5} mb={2}>
            {/* H2H */}
            <Grid size={{ xs: 4 }}>
              <Box textAlign="center" sx={{ bgcolor: "rgba(255,255,255,0.03)", borderRadius: 1, p: 1 }}>
                <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
                  H2H
                </Typography>
                <Typography variant="body2" fontWeight={700} color="white">
                  {prediction.h2h.total_matches > 0
                    ? `${prediction.h2h.p1_wins} - ${prediction.h2h.p2_wins}`
                    : "Sin datos"}
                </Typography>
              </Box>
            </Grid>

            {/* Surface Win Rate */}
            <Grid size={{ xs: 4 }}>
              <Box textAlign="center" sx={{ bgcolor: "rgba(255,255,255,0.03)", borderRadius: 1, p: 1 }}>
                <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
                  Win% en {match.surface}
                </Typography>
                <Box display="flex" justifyContent="center" gap={1}>
                  <Typography
                    variant="body2"
                    fontWeight={700}
                    sx={{ color: getWinRateColor(prediction.surface_stats.p1_surface_win_rate) }}
                  >
                    {(prediction.surface_stats.p1_surface_win_rate * 100).toFixed(0)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">vs</Typography>
                  <Typography
                    variant="body2"
                    fontWeight={700}
                    sx={{ color: getWinRateColor(prediction.surface_stats.p2_surface_win_rate) }}
                  >
                    {(prediction.surface_stats.p2_surface_win_rate * 100).toFixed(0)}%
                  </Typography>
                </Box>
              </Box>
            </Grid>

            {/* Recent Form */}
            <Grid size={{ xs: 4 }}>
              <Box textAlign="center" sx={{ bgcolor: "rgba(255,255,255,0.03)", borderRadius: 1, p: 1 }}>
                <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
                  Forma (5)
                </Typography>
                <Box display="flex" justifyContent="center" gap={1}>
                  <Typography
                    variant="body2"
                    fontWeight={700}
                    sx={{ color: getWinRateColor(prediction.form.p1_win_rate_5) }}
                  >
                    {(prediction.form.p1_win_rate_5 * 100).toFixed(0)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">vs</Typography>
                  <Typography
                    variant="body2"
                    fontWeight={700}
                    sx={{ color: getWinRateColor(prediction.form.p2_win_rate_5) }}
                  >
                    {(prediction.form.p2_win_rate_5 * 100).toFixed(0)}%
                  </Typography>
                </Box>
              </Box>
            </Grid>
          </Grid>

          {/* Key Factors */}
          {prediction.key_factors.length > 0 && (
            <Box mb={2}>
              <Typography variant="caption" color="text.secondary" display="block" mb={1}>
                Factores clave:
              </Typography>
              <Box display="flex" flexDirection="column" gap={0.5}>
                {prediction.key_factors.slice(0, 3).map((factor, idx) => (
                  <Box key={idx} display="flex" alignItems="center" gap={0.5}>
                    <CheckCircle sx={{ fontSize: 12, color: "#10b981" }} />
                    <Typography variant="caption" color="rgba(255,255,255,0.7)">
                      {factor}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          )}

          {/* Value Bet Indicator */}
          {prediction.value_bets.length > 0 && (
            <Box
              mb={2}
              sx={{
                bgcolor: "rgba(16,185,129,0.1)",
                border: "1px solid rgba(16,185,129,0.3)",
                borderRadius: 2,
                p: 1.5,
              }}
            >
              <Box display="flex" alignItems="center" gap={0.5} mb={1}>
                <Star sx={{ fontSize: 16, color: "#10b981" }} />
                <Typography variant="caption" fontWeight={700} sx={{ color: "#10b981" }}>
                  VALUE BET DETECTADO
                </Typography>
              </Box>
              {prediction.value_bets.map((bet, idx) => (
                <Box key={idx} display="flex" justifyContent="space-between" alignItems="center">
                  <Typography variant="caption" color="rgba(255,255,255,0.9)">
                    {bet.player} @ {bet.odds}
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="caption" color="text.secondary">
                      Implícita: {bet.implied_prob}% → Modelo: {bet.model_prob}%
                    </Typography>
                    <Chip
                      label={`+${bet.edge}%`}
                      size="small"
                      sx={{
                        bgcolor: "#10b981",
                        color: "white",
                        fontWeight: 700,
                        fontSize: "0.65rem",
                        height: 18,
                      }}
                    />
                  </Box>
                </Box>
              ))}
            </Box>
          )}

          {/* Confidence + Recommendation */}
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            sx={{
              bgcolor: "rgba(255,255,255,0.03)",
              borderRadius: 2,
              p: 1.5,
            }}
          >
            <Box display="flex" alignItems="center" gap={0.5}>
              <Box
                sx={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  bgcolor: getConfidenceColor(),
                }}
              />
              <Typography variant="caption" color="text.secondary">
                Confianza: {confidencePercent.toFixed(0)}%
              </Typography>
              {match.best_of === 5 && (
                <Chip
                  label="Best of 5"
                  size="small"
                  sx={{
                    ml: 1,
                    height: 16,
                    fontSize: "0.6rem",
                    bgcolor: "rgba(255,255,255,0.06)",
                    color: "rgba(255,255,255,0.5)",
                  }}
                />
              )}
            </Box>

            {/* Recommended Bet */}
            <Box display="flex" alignItems="center" gap={0.5}>
              <SportsMma sx={{ fontSize: 14, color: "#f59e0b" }} />
              <Typography variant="caption" fontWeight={600} sx={{ color: "#f59e0b" }}>
                {isP1Winner ? match.player1.name : match.player2.name} ML
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Modal */}
      <TennisMatchDetailsModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        match={match}
      />
    </>
  );
};

export default TennisMatchCard;

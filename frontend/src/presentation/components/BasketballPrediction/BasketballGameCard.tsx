import React, { useState } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Divider,
} from "@mui/material";
import {
  TrendingUp,
  SportsBasketball,
  Star,
  CheckCircle,
} from "@mui/icons-material";
import { BasketballGameWithPrediction } from "../../../types";
import BasketballGameDetailsModal from "./BasketballGameDetailsModal";

interface BasketballGameCardProps {
  game: BasketballGameWithPrediction;
}

const BasketballGameCard: React.FC<BasketballGameCardProps> = ({ game }) => {
  const [modalOpen, setModalOpen] = useState(false);
  const { prediction } = game;
  const homeWin = prediction.home_win_prob * 100;
  const awayWin = prediction.away_win_prob * 100;
  const isHomeWinner = prediction.predicted_winner === "Home";
  const confidencePercent = prediction.confidence * 100;

  const getConfidenceColor = () => {
    if (confidencePercent >= 70) return "#10b981";
    if (confidencePercent >= 40) return "#f59e0b";
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
          {/* Header: Venue */}
          <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
            <Box display="flex" alignItems="center" gap={1}>
              <SportsBasketball sx={{ color: "#f59e0b", fontSize: 18 }} />
              <Typography variant="subtitle2" fontWeight={600} color="rgba(255,255,255,0.9)">
                {game.venue || "NBA"}
              </Typography>
            </Box>
          </Box>

          {/* Teams */}
          <Grid container spacing={1} alignItems="center" mb={2}>
            {/* Home Team */}
            <Grid size={{ xs: 5 }}>
              <Box
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  bgcolor: isHomeWinner ? "rgba(99,102,241,0.12)" : "transparent",
                  border: isHomeWinner ? "1px solid rgba(99,102,241,0.25)" : "1px solid transparent",
                }}
              >
                <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
                  {isHomeWinner && <TrendingUp sx={{ color: "#6366f1", fontSize: 16 }} />}
                  <Typography
                    variant="body1"
                    fontWeight={isHomeWinner ? 700 : 500}
                    sx={{ color: isHomeWinner ? "#a5b4fc" : "rgba(255,255,255,0.9)" }}
                  >
                    {game.home_team}
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary" display="block">
                  🏠 {game.home_team_name || "Home"}
                </Typography>
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

            {/* Away Team */}
            <Grid size={{ xs: 5 }}>
              <Box
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  bgcolor: !isHomeWinner ? "rgba(16,185,129,0.12)" : "transparent",
                  border: !isHomeWinner ? "1px solid rgba(16,185,129,0.25)" : "1px solid transparent",
                }}
                textAlign="right"
              >
                <Box display="flex" alignItems="center" justifyContent="flex-end" gap={0.5} mb={0.5}>
                  <Typography
                    variant="body1"
                    fontWeight={!isHomeWinner ? 700 : 500}
                    sx={{ color: !isHomeWinner ? "#6ee7b7" : "rgba(255,255,255,0.9)" }}
                  >
                    {game.away_team}
                  </Typography>
                  {!isHomeWinner && <TrendingUp sx={{ color: "#10b981", fontSize: 16 }} />}
                </Box>
                <Typography variant="caption" color="text.secondary" display="block" textAlign="right">
                  ✈️ {game.away_team_name || "Away"}
                </Typography>
              </Box>
            </Grid>
          </Grid>

          {/* Probability Bar */}
          <Box mb={2}>
            <Box display="flex" justifyContent="space-between" mb={0.5}>
              <Typography
                variant="caption"
                fontWeight={600}
                sx={{ color: isHomeWinner ? "#a5b4fc" : "rgba(255,255,255,0.5)" }}
              >
                {homeWin.toFixed(0)}%
              </Typography>
              <Typography
                variant="caption"
                fontWeight={600}
                sx={{ color: !isHomeWinner ? "#6ee7b7" : "rgba(255,255,255,0.5)" }}
              >
                {awayWin.toFixed(0)}%
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
                  width: `${homeWin}%`,
                  background: isHomeWinner
                    ? "linear-gradient(90deg, #6366f1, #818cf8)"
                    : "rgba(99,102,241,0.4)",
                  borderRadius: "3px 0 0 3px",
                  transition: "width 0.6s ease",
                }}
              />
              <Box
                sx={{
                  width: `${awayWin}%`,
                  background: !isHomeWinner
                    ? "linear-gradient(90deg, #10b981, #34d399)"
                    : "rgba(16,185,129,0.4)",
                  borderRadius: "0 3px 3px 0",
                  transition: "width 0.6s ease",
                }}
              />
            </Box>
          </Box>

          <Divider sx={{ borderColor: "rgba(255,255,255,0.06)", mb: 2 }} />

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
          {prediction.markets.some(m => m.is_recommended) && (
            <Box
              mb={2}
              sx={{
                bgcolor: "rgba(16,185,129,0.1)",
                border: "1px solid rgba(16,185,129,0.3)",
                borderRadius: 2,
                p: 1.5,
              }}
            >
              <Box display="flex" alignItems="center" gap={0.5}>
                <Star sx={{ fontSize: 16, color: "#10b981" }} />
                <Typography variant="caption" fontWeight={700} sx={{ color: "#10b981" }}>
                  MERCADO RECOMENDADO
                </Typography>
              </Box>
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
            </Box>

            <Box display="flex" alignItems="center" gap={0.5}>
              <SportsBasketball sx={{ fontSize: 14, color: "#f59e0b" }} />
              <Typography variant="caption" fontWeight={600} sx={{ color: "#f59e0b" }}>
                {isHomeWinner ? game.home_team : game.away_team} ML
              </Typography>
            </Box>
          </Box>
        </CardContent>
      </Card>

      {/* Modal */}
      <BasketballGameDetailsModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        game={game}
      />
    </>
  );
};

export default BasketballGameCard;

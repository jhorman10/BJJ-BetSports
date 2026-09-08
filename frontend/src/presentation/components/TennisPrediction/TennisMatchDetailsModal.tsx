import React, { useState } from "react";
import {
  Box,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Chip,
  Tabs,
  Tab,
  Grid,
  Divider,
  IconButton,
} from "@mui/material";
import {
  Close,
  EmojiEvents,
  TrendingUp,
  Star,
  SportsMma,
} from "@mui/icons-material";

import { TennisUpcomingMatch, TennisMarket } from "../../../types";

import {
  TENNIS_CATEGORY_TABS,
  getMarketIcon,
  getConfidenceColor,
  getProbabilityColor,
  groupMarketsByCategory,
} from "./tennisMarketUtils";

interface TennisMatchDetailsModalProps {
  open: boolean;
  onClose: () => void;
  match: TennisUpcomingMatch | null;
}

const SURFACE_COLORS: Record<string, string> = {
  Hard: "#3b82f6",
  Clay: "#f97316",
  Grass: "#22c55e",
  "Hard (Indoor)": "#6366f1",
  Carpet: "#a855f7",
};

const TennisMatchDetailsModal: React.FC<TennisMatchDetailsModalProps> = ({
  open,
  onClose,
  match,
}) => {
  const [activeTab, setActiveTab] = useState(0);

  if (!match) return null;

  const { prediction } = match;
  const p1Win = prediction.p1_win_prob * 100;
  const p2Win = prediction.p2_win_prob * 100;
  const isP1Winner = prediction.predicted_winner === "Player 1";
  const surfaceColor = SURFACE_COLORS[match.surface] || "#6366f1";

  // Group markets by category
  const groupedMarkets = groupMarketsByCategory(prediction.markets || []);
  const activeCategory = TENNIS_CATEGORY_TABS[activeTab];
  const activeMarkets = groupedMarkets.get(activeCategory?.key) || [];

  // Filter tabs that have markets
  const availableTabs = TENNIS_CATEGORY_TABS.filter(
    (tab) => (groupedMarkets.get(tab.key) || []).length > 0
  );

  const renderMarketRow = (market: TennisMarket) => {
    const prob = market.probability * 100;
    const probColor = getProbabilityColor(market.probability);
    const confColor = getConfidenceColor(market.confidence_level);

    return (
      <Box
        key={market.pick_code}
        sx={{
          p: 1.5,
          mb: 1,
          borderRadius: 2,
          bgcolor: "rgba(255,255,255,0.03)",
          border: market.is_recommended
            ? "1px solid rgba(16,185,129,0.3)"
            : "1px solid transparent",
          "&:hover": {
            bgcolor: "rgba(255,255,255,0.05)",
          },
        }}
      >
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={0.5}>
          <Box display="flex" alignItems="center" gap={1}>
            <Typography variant="body2" fontWeight={600} color="white">
              {getMarketIcon(market.market_type)} {market.market_label}
            </Typography>
            {market.is_recommended && (
              <Chip
                label="RECOMENDADO"
                size="small"
                sx={{
                  bgcolor: "#10b981",
                  color: "white",
                  fontWeight: 700,
                  fontSize: "0.6rem",
                  height: 18,
                }}
              />
            )}
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip
              label={market.confidence_level.toUpperCase()}
              size="small"
              sx={{
                bgcolor: `${confColor}20`,
                color: confColor,
                fontWeight: 600,
                fontSize: "0.65rem",
                height: 18,
              }}
            />
            <Chip
              label={`${prob.toFixed(0)}%`}
              size="small"
              sx={{
                bgcolor: `${probColor}20`,
                color: probColor,
                fontWeight: 700,
                fontSize: "0.7rem",
                height: 20,
              }}
            />
          </Box>
        </Box>

        {/* Probability Bar */}
        <Box sx={{ height: 4, borderRadius: 2, bgcolor: "rgba(255,255,255,0.06)", overflow: "hidden", mb: 0.5 }}>
          <Box
            sx={{
              width: `${prob}%`,
              height: "100%",
              bgcolor: probColor,
              borderRadius: 2,
              transition: "width 0.6s ease",
            }}
          />
        </Box>

        <Typography variant="caption" color="text.secondary" fontStyle="italic">
          {market.reasoning}
        </Typography>
      </Box>
    );
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          background: "linear-gradient(165deg, rgba(20,25,35,0.98) 0%, rgba(10,15,25,0.99) 100%)",
          border: "1px solid rgba(255,255,255,0.1)",
          borderRadius: "24px",
          maxHeight: "90vh",
        },
      }}
      TransitionProps={{
        timeout: { enter: 300, exit: 200 },
      }}
    >
      {/* Header */}
      <DialogTitle sx={{ pb: 1 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box display="flex" alignItems="center" gap={1}>
            <EmojiEvents sx={{ color: "#f59e0b" }} />
            <Typography variant="h6" fontWeight={700} color="white">
              {match.tournament}
            </Typography>
            <Chip
              label={match.surface}
              size="small"
              sx={{ bgcolor: surfaceColor, color: "white", fontWeight: 600 }}
            />
            <Chip
              label={match.round}
              size="small"
              variant="outlined"
              sx={{ borderColor: "rgba(255,255,255,0.2)", color: "rgba(255,255,255,0.7)" }}
            />
          </Box>
          <IconButton onClick={onClose} sx={{ color: "rgba(255,255,255,0.5)" }}>
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ pt: 0 }}>
        {/* Players + Probability */}
        <Box mb={3}>
          <Grid container spacing={2} alignItems="center" mb={2}>
            <Grid size={{ xs: 5 }}>
              <Box
                sx={{
                  p: 2,
                  borderRadius: 2,
                  bgcolor: isP1Winner ? "rgba(99,102,241,0.12)" : "transparent",
                  border: isP1Winner ? "1px solid rgba(99,102,241,0.25)" : "1px solid transparent",
                }}
              >
                <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
                  {isP1Winner && <TrendingUp sx={{ color: "#6366f1", fontSize: 18 }} />}
                  <Typography variant="h6" fontWeight={700} sx={{ color: isP1Winner ? "#a5b4fc" : "white" }}>
                    {match.player1.name}
                  </Typography>
                </Box>
                <Box display="flex" gap={0.5}>
                  {match.player1.rank && (
                    <Chip label={`#${match.player1.rank}`} size="small" sx={{ bgcolor: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.7)" }} />
                  )}
                  {match.player1.seed && (
                    <Chip label={`S${match.player1.seed}`} size="small" sx={{ bgcolor: "rgba(245,158,11,0.15)", color: "#f59e0b" }} />
                  )}
                </Box>
              </Box>
            </Grid>
            <Grid size={{ xs: 2 }}>
              <Box textAlign="center">
                <Typography variant="h4" fontWeight={700} color="text.secondary">VS</Typography>
              </Box>
            </Grid>
            <Grid size={{ xs: 5 }}>
              <Box
                sx={{
                  p: 2,
                  borderRadius: 2,
                  bgcolor: !isP1Winner ? "rgba(16,185,129,0.12)" : "transparent",
                  border: !isP1Winner ? "1px solid rgba(16,185,129,0.25)" : "1px solid transparent",
                }}
                textAlign="right"
              >
                <Box display="flex" alignItems="center" justifyContent="flex-end" gap={0.5} mb={0.5}>
                  <Typography variant="h6" fontWeight={700} sx={{ color: !isP1Winner ? "#6ee7b7" : "white" }}>
                    {match.player2.name}
                  </Typography>
                  {!isP1Winner && <TrendingUp sx={{ color: "#10b981", fontSize: 18 }} />}
                </Box>
                <Box display="flex" gap={0.5} justifyContent="flex-end">
                  {match.player2.seed && (
                    <Chip label={`S${match.player2.seed}`} size="small" sx={{ bgcolor: "rgba(245,158,11,0.15)", color: "#f59e0b" }} />
                  )}
                  {match.player2.rank && (
                    <Chip label={`#${match.player2.rank}`} size="small" sx={{ bgcolor: "rgba(255,255,255,0.08)", color: "rgba(255,255,255,0.7)" }} />
                  )}
                </Box>
              </Box>
            </Grid>
          </Grid>

          {/* Probability Bar */}
          <Box mb={2}>
            <Box display="flex" justifyContent="space-between" mb={0.5}>
              <Typography variant="body2" fontWeight={600} sx={{ color: isP1Winner ? "#a5b4fc" : "rgba(255,255,255,0.5)" }}>
                {p1Win.toFixed(1)}%
              </Typography>
              <Typography variant="body2" fontWeight={600} sx={{ color: !isP1Winner ? "#6ee7b7" : "rgba(255,255,255,0.5)" }}>
                {p2Win.toFixed(1)}%
              </Typography>
            </Box>
            <Box sx={{ height: 8, borderRadius: 4, bgcolor: "rgba(255,255,255,0.06)", overflow: "hidden", display: "flex" }}>
              <Box sx={{ width: `${p1Win}%`, background: isP1Winner ? "linear-gradient(90deg, #6366f1, #818cf8)" : "rgba(99,102,241,0.4)", borderRadius: "4px 0 0 4px", transition: "width 0.6s ease" }} />
              <Box sx={{ width: `${p2Win}%`, background: !isP1Winner ? "linear-gradient(90deg, #10b981, #34d399)" : "rgba(16,185,129,0.4)", borderRadius: "0 4px 4px 0", transition: "width 0.6s ease" }} />
            </Box>
          </Box>

          {/* Stats Grid */}
          <Grid container spacing={1.5} mb={2}>
            <Grid size={{ xs: 4 }}>
              <Box textAlign="center" sx={{ bgcolor: "rgba(255,255,255,0.03)", borderRadius: 1, p: 1 }}>
                <Typography variant="caption" color="text.secondary" display="block">H2H</Typography>
                <Typography variant="body2" fontWeight={700} color="white">
                  {prediction.h2h.total_matches > 0 ? `${prediction.h2h.p1_wins} - ${prediction.h2h.p2_wins}` : "Sin datos"}
                </Typography>
              </Box>
            </Grid>
            <Grid size={{ xs: 4 }}>
              <Box textAlign="center" sx={{ bgcolor: "rgba(255,255,255,0.03)", borderRadius: 1, p: 1 }}>
                <Typography variant="caption" color="text.secondary" display="block">Win% {match.surface}</Typography>
                <Box display="flex" justifyContent="center" gap={1}>
                  <Typography variant="body2" fontWeight={700} sx={{ color: getProbabilityColor(prediction.surface_stats.p1_surface_win_rate) }}>
                    {(prediction.surface_stats.p1_surface_win_rate * 100).toFixed(0)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">vs</Typography>
                  <Typography variant="body2" fontWeight={700} sx={{ color: getProbabilityColor(prediction.surface_stats.p2_surface_win_rate) }}>
                    {(prediction.surface_stats.p2_surface_win_rate * 100).toFixed(0)}%
                  </Typography>
                </Box>
              </Box>
            </Grid>
            <Grid size={{ xs: 4 }}>
              <Box textAlign="center" sx={{ bgcolor: "rgba(255,255,255,0.03)", borderRadius: 1, p: 1 }}>
                <Typography variant="caption" color="text.secondary" display="block">Forma (5)</Typography>
                <Box display="flex" justifyContent="center" gap={1}>
                  <Typography variant="body2" fontWeight={700} sx={{ color: getProbabilityColor(prediction.form.p1_win_rate_5) }}>
                    {(prediction.form.p1_win_rate_5 * 100).toFixed(0)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">vs</Typography>
                  <Typography variant="body2" fontWeight={700} sx={{ color: getProbabilityColor(prediction.form.p2_win_rate_5) }}>
                    {(prediction.form.p2_win_rate_5 * 100).toFixed(0)}%
                  </Typography>
                </Box>
              </Box>
            </Grid>
          </Grid>

          {/* Key Factors */}
          {prediction.key_factors.length > 0 && (
            <Box mb={2}>
              <Typography variant="caption" color="text.secondary" display="block" mb={1}>Factores clave:</Typography>
              <Box display="flex" flexDirection="column" gap={0.5}>
                {prediction.key_factors.map((factor, idx) => (
                  <Box key={idx} display="flex" alignItems="center" gap={0.5}>
                    <Star sx={{ fontSize: 12, color: "#f59e0b" }} />
                    <Typography variant="caption" color="rgba(255,255,255,0.7)">{factor}</Typography>
                  </Box>
                ))}
              </Box>
            </Box>
          )}

          {/* Value Bet */}
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
                <Typography variant="caption" fontWeight={700} sx={{ color: "#10b981" }}>VALUE BET DETECTADO</Typography>
              </Box>
              {prediction.value_bets.map((bet, idx) => (
                <Box key={idx} display="flex" justifyContent="space-between" alignItems="center">
                  <Typography variant="caption" color="rgba(255,255,255,0.9)">{bet.player} @ {bet.odds}</Typography>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="caption" color="text.secondary">Implícita: {bet.implied_prob}% → Modelo: {bet.model_prob}%</Typography>
                    <Chip label={`+${bet.edge}%`} size="small" sx={{ bgcolor: "#10b981", color: "white", fontWeight: 700, fontSize: "0.65rem", height: 18 }} />
                  </Box>
                </Box>
              ))}
            </Box>
          )}
        </Box>

        <Divider sx={{ borderColor: "rgba(255,255,255,0.06)", mb: 2 }} />

        {/* Markets Section */}
        <Box>
          <Typography variant="subtitle1" fontWeight={700} color="white" mb={2}>
            Mercados Disponibles
          </Typography>

          {/* Category Tabs */}
          <Tabs
            value={activeTab}
            onChange={(_, newValue) => setActiveTab(newValue)}
            variant="scrollable"
            scrollButtons="auto"
            sx={{
              mb: 2,
              "& .MuiTab-root": {
                color: "rgba(255,255,255,0.5)",
                fontWeight: 600,
                textTransform: "none",
                minHeight: 36,
              },
              "& .Mui-selected": {
                color: "#6366f1 !important",
              },
              "& .MuiTabs-indicator": {
                bgcolor: "#6366f1",
              },
            }}
          >
            {availableTabs.map((tab) => {
              const count = (groupedMarkets.get(tab.key) || []).length;
              return (
                <Tab
                  key={tab.key}
                  label={`${tab.icon} ${tab.label} (${count})`}
                />
              );
            })}
          </Tabs>

          {/* Market List */}
          <Box sx={{ maxHeight: 300, overflow: "auto" }}>
            {activeMarkets.length > 0 ? (
              activeMarkets.map((market) => renderMarketRow(market))
            ) : (
              <Box textAlign="center" py={3}>
                <Typography variant="body2" color="text.secondary">
                  No hay mercados disponibles en esta categoría
                </Typography>
              </Box>
            )}
          </Box>
        </Box>

        {/* Recommended Bet Footer */}
        <Box
          mt={2}
          p={2}
          sx={{
            bgcolor: "rgba(245,158,11,0.1)",
            border: "1px solid rgba(245,158,11,0.3)",
            borderRadius: 2,
          }}
        >
          <Box display="flex" alignItems="center" gap={1}>
            <SportsMma sx={{ color: "#f59e0b" }} />
            <Typography variant="body2" fontWeight={600} sx={{ color: "#f59e0b" }}>
              Recomendación: {isP1Winner ? match.player1.name : match.player2.name} ML
            </Typography>
            <Typography variant="caption" color="text.secondary">
              — Confianza {(prediction.confidence * 100).toFixed(0)}%
            </Typography>
          </Box>
        </Box>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button
          onClick={onClose}
          sx={{
            color: "rgba(255,255,255,0.7)",
            textTransform: "none",
            borderRadius: 2,
          }}
        >
          Cerrar
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default TennisMatchDetailsModal;

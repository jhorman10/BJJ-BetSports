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
  SportsBasketball,
  TrendingUp,
  Star,
} from "@mui/icons-material";
import { BasketballGameWithPrediction, BasketballMarket } from "../../../types";
import {
  BASKETBALL_CATEGORY_TABS,
  getMarketIcon,
  getConfidenceColor,
  getProbabilityColor,
  groupMarketsByCategory,
} from "./basketballMarketUtils";

interface BasketballGameDetailsModalProps {
  open: boolean;
  onClose: () => void;
  game: BasketballGameWithPrediction | null;
}

const BasketballGameDetailsModal: React.FC<BasketballGameDetailsModalProps> = ({
  open,
  onClose,
  game,
}) => {
  const [activeTab, setActiveTab] = useState(0);

  if (!game) return null;

  const { prediction } = game;
  const homeWin = prediction.home_win_prob * 100;
  const awayWin = prediction.away_win_prob * 100;
  const isHomeWinner = prediction.predicted_winner === "Home";

  const groupedMarkets = groupMarketsByCategory(prediction.markets || []);
  const activeCategory = BASKETBALL_CATEGORY_TABS[activeTab];
  const activeMarkets = groupedMarkets.get(activeCategory?.key) || [];
  const availableTabs = BASKETBALL_CATEGORY_TABS.filter(
    (tab) => (groupedMarkets.get(tab.key) || []).length > 0
  );

  const renderMarketRow = (market: BasketballMarket) => {
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
          "&:hover": { bgcolor: "rgba(255,255,255,0.05)" },
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
                sx={{ bgcolor: "#10b981", color: "white", fontWeight: 700, fontSize: "0.6rem", height: 18 }}
              />
            )}
          </Box>
          <Box display="flex" alignItems="center" gap={1}>
            <Chip
              label={market.confidence_level.toUpperCase()}
              size="small"
              sx={{ bgcolor: `${confColor}20`, color: confColor, fontWeight: 600, fontSize: "0.65rem", height: 18 }}
            />
            <Chip
              label={`${prob.toFixed(0)}%`}
              size="small"
              sx={{ bgcolor: `${probColor}20`, color: probColor, fontWeight: 700, fontSize: "0.7rem", height: 20 }}
            />
          </Box>
        </Box>
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
      TransitionProps={{ timeout: { enter: 300, exit: 200 } }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box display="flex" alignItems="center" gap={1}>
            <SportsBasketball sx={{ color: "#f59e0b" }} />
            <Typography variant="h6" fontWeight={700} color="white">
              {game.home_team} vs {game.away_team}
            </Typography>
          </Box>
          <IconButton onClick={onClose} sx={{ color: "rgba(255,255,255,0.5)" }}>
            <Close />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent sx={{ pt: 0 }}>
        {/* Teams + Probability */}
        <Box mb={3}>
          <Grid container spacing={2} alignItems="center" mb={2}>
            <Grid size={{ xs: 5 }}>
              <Box
                sx={{
                  p: 2,
                  borderRadius: 2,
                  bgcolor: isHomeWinner ? "rgba(99,102,241,0.12)" : "transparent",
                  border: isHomeWinner ? "1px solid rgba(99,102,241,0.25)" : "1px solid transparent",
                }}
              >
                <Box display="flex" alignItems="center" gap={0.5} mb={0.5}>
                  {isHomeWinner && <TrendingUp sx={{ color: "#6366f1", fontSize: 18 }} />}
                  <Typography variant="h6" fontWeight={700} sx={{ color: isHomeWinner ? "#a5b4fc" : "white" }}>
                    {game.home_team}
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary">
                  🏠 Local — {game.home_team_name || "Home"}
                </Typography>
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
                  bgcolor: !isHomeWinner ? "rgba(16,185,129,0.12)" : "transparent",
                  border: !isHomeWinner ? "1px solid rgba(16,185,129,0.25)" : "1px solid transparent",
                }}
                textAlign="right"
              >
                <Box display="flex" alignItems="center" justifyContent="flex-end" gap={0.5} mb={0.5}>
                  <Typography variant="h6" fontWeight={700} sx={{ color: !isHomeWinner ? "#6ee7b7" : "white" }}>
                    {game.away_team}
                  </Typography>
                  {!isHomeWinner && <TrendingUp sx={{ color: "#10b981", fontSize: 18 }} />}
                </Box>
                <Typography variant="caption" color="text.secondary">
                  ✈️ Visitante — {game.away_team_name || "Away"}
                </Typography>
              </Box>
            </Grid>
          </Grid>

          {/* Probability Bar */}
          <Box mb={2}>
            <Box display="flex" justifyContent="space-between" mb={0.5}>
              <Typography variant="body2" fontWeight={600} sx={{ color: isHomeWinner ? "#a5b4fc" : "rgba(255,255,255,0.5)" }}>
                {homeWin.toFixed(1)}%
              </Typography>
              <Typography variant="body2" fontWeight={600} sx={{ color: !isHomeWinner ? "#6ee7b7" : "rgba(255,255,255,0.5)" }}>
                {awayWin.toFixed(1)}%
              </Typography>
            </Box>
            <Box sx={{ height: 8, borderRadius: 4, bgcolor: "rgba(255,255,255,0.06)", overflow: "hidden", display: "flex" }}>
              <Box sx={{ width: `${homeWin}%`, background: isHomeWinner ? "linear-gradient(90deg, #6366f1, #818cf8)" : "rgba(99,102,241,0.4)", borderRadius: "4px 0 0 4px", transition: "width 0.6s ease" }} />
              <Box sx={{ width: `${awayWin}%`, background: !isHomeWinner ? "linear-gradient(90deg, #10b981, #34d399)" : "rgba(16,185,129,0.4)", borderRadius: "0 4px 4px 0", transition: "width 0.6s ease" }} />
            </Box>
          </Box>

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
        </Box>

        <Divider sx={{ borderColor: "rgba(255,255,255,0.06)", mb: 2 }} />

        {/* Markets Section */}
        <Box>
          <Typography variant="subtitle1" fontWeight={700} color="white" mb={2}>
            Mercados Disponibles
          </Typography>
          <Tabs
            value={activeTab}
            onChange={(_, newValue) => setActiveTab(newValue)}
            variant="scrollable"
            scrollButtons="auto"
            sx={{
              mb: 2,
              "& .MuiTab-root": { color: "rgba(255,255,255,0.5)", fontWeight: 600, textTransform: "none", minHeight: 36 },
              "& .Mui-selected": { color: "#6366f1 !important" },
              "& .MuiTabs-indicator": { bgcolor: "#6366f1" },
            }}
          >
            {availableTabs.map((tab) => {
              const count = (groupedMarkets.get(tab.key) || []).length;
              return (
                <Tab key={tab.key} label={`${tab.icon} ${tab.label} (${count})`} />
              );
            })}
          </Tabs>
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
            <SportsBasketball sx={{ color: "#f59e0b" }} />
            <Typography variant="body2" fontWeight={600} sx={{ color: "#f59e0b" }}>
              Recomendación: {isHomeWinner ? game.home_team : game.away_team} ML
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
          sx={{ color: "rgba(255,255,255,0.7)", textTransform: "none", borderRadius: 2 }}
        >
          Cerrar
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default BasketballGameDetailsModal;

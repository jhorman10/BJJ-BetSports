import React, { useMemo } from "react";
import { useLocation } from "react-router-dom";
import {
  Paper,
  Box,
  Typography,
  List,
  ListItem,
  IconButton,
  Chip,
  Button,
  Collapse,
} from "@mui/material";
import {
  Close,
  DeleteOutline,
  LocalActivity,
  ExpandLess,
  ExpandMore,
  Diamond,
  SportsSoccer,
  Flag,
  Style,
  EmojiEvents,
} from "@mui/icons-material";

import { useParleyStore } from "../../../application/stores/useParleyStore";
import { useUIStore } from "../../../application/stores/useUIStore";
import { getTeamDisplayName } from "../../../utils/teamUtils";

// Helper to map pick codes to icons
const getPickIcon = (pick: string, label: string): React.ReactElement => {
  const p = pick.toUpperCase();
  const l = label.toUpperCase();

  if (l.includes("CÓRNER") || l.includes("CORNER") || p.includes("CORNER"))
    return <Flag sx={{ fontSize: "1rem !important" }} />;
  if (l.includes("TARJETA") || l.includes("CARD") || p.includes("CARD"))
    return <Style sx={{ fontSize: "1rem !important" }} />; // Cards
  if (
    l.includes("GOL") ||
    p.includes("OVER") ||
    p.includes("UNDER") ||
    p.includes("BTTS")
  )
    return <SportsSoccer sx={{ fontSize: "1rem !important" }} />;
  if (
    p.includes("WIN") ||
    p.includes("HOME") ||
    p.includes("AWAY") ||
    p === "1" ||
    p === "2" ||
    p === "X"
  )
    return <EmojiEvents sx={{ fontSize: "1rem !important" }} />;

  return <LocalActivity sx={{ fontSize: "1rem !important" }} />;
};

const ParleySlip: React.FC = () => {
  const { selectedPicks, removePick, clearPicks } = useParleyStore();
  const { isParleySlipOpen, toggleParleySlip } = useUIStore();

  const items = useMemo(() => Object.values(selectedPicks), [selectedPicks]);

  const stats = useMemo(() => {
    if (items.length === 0) return { totalProb: 0, combinedOdds: 0 };

    // Simple probability multiplication (assuming independence)
    const totalProb = items.reduce((acc, curr) => {
      return acc * curr.probability;
    }, 1.0);

    // Mock Odds Calculation (since we might not have exact odds for every market)
    // 1 / prob is "fair odds", we add margin
    const combinedOdds = totalProb > 0 ? 1 / totalProb : 0;

    return {
      totalProb: totalProb * 100,
      combinedOdds: combinedOdds.toFixed(2),
    };
  }, [items]);

  const location = useLocation();

  if (items.length === 0 || location.pathname === '/parley-calculator') return null;

  return (
    <Paper
      elevation={4}
      sx={{
        position: "fixed",
        bottom: 0,
        right: { xs: 0, md: 32 },
        width: { xs: "100%", md: 350 },
        borderTopLeftRadius: 16,
        borderTopRightRadius: 16,
        zIndex: 1200,
        overflow: "hidden",
        pb: "env(safe-area-inset-bottom, 0px)",
        bgcolor: "#1e293b",
        border: "1px solid rgba(255,255,255,0.1)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          px: { xs: 2, sm: 2 },
          py: { xs: 1, sm: 2 },
          bgcolor: "#0f172a",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          cursor: "pointer",
          borderBottom: "1px solid rgba(255,255,255,0.1)",
        }}
        onClick={toggleParleySlip}
      >
        <Box sx={{ display: "flex", alignItems: "center" }}>
          <LocalActivity sx={{ color: "#6366f1", mr: 1, fontSize: { xs: "1.2rem", sm: "1.5rem" } }} />
          <Typography variant="subtitle1" fontWeight="bold" color="white" sx={{ fontSize: { xs: "0.875rem", sm: "1rem" } }}>
            Mi Parley
          </Typography>
          <Chip
            label={items.length}
            size="small"
            color="primary"
            sx={{ ml: 1, height: { xs: 18, sm: 20 }, minWidth: { xs: 18, sm: 20 }, fontSize: { xs: "0.7rem", sm: "0.8rem" } }}
          />
        </Box>
        <IconButton size="small" sx={{ color: "text.secondary" }}>
          {isParleySlipOpen ? <ExpandMore /> : <ExpandLess />}
        </IconButton>
      </Box>

      {/* Content */}
      <Collapse in={isParleySlipOpen}>
        <Box sx={{ p: 0, maxHeight: { xs: 300, sm: 400 }, overflowY: "auto" }}>
          <List disablePadding>
            {items.map((item) => (
              <ListItem
                key={item.match.match.id}
                sx={{
                  borderBottom: "1px solid rgba(255,255,255,0.05)",
                  flexDirection: "column",
                  alignItems: "flex-start",
                  py: 1.5,
                }}
              >
                <Box
                  sx={{
                    width: "100%",
                    display: "flex",
                    justifyContent: "space-between",
                    mb: 0.5,
                  }}
                >
                  <Typography variant="caption" color="text.secondary">
                    {getTeamDisplayName(item.match.match.home_team)} vs{" "}
                    {getTeamDisplayName(item.match.match.away_team)}
                  </Typography>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      removePick(item.match.match.id);
                    }}
                    sx={{ p: 0.5, color: "error.main" }}
                  >
                    <Close fontSize="small" />
                  </IconButton>
                </Box>

                <Box
                  sx={{
                    width: "100%",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <Box display="flex" alignItems="center" gap={1}>
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: 28,
                        height: 28,
                        borderRadius: "50%",
                        bgcolor: "rgba(139, 92, 246, 0.2)",
                        color: "#a78bfa",
                        border: "1px solid rgba(139, 92, 246, 0.3)",
                      }}
                    >
                      {getPickIcon(item.pick, item.label)}
                    </Box>
                    <Typography variant="body2" color="white" fontWeight="bold">
                      {item.label}
                    </Typography>
                  </Box>

                  <Box display="flex" alignItems="center" gap={1}>
                    {item.match.prediction.is_value_bet && (
                      <Chip
                        icon={
                          <Diamond
                            sx={{
                              fontSize: "0.8rem !important",
                              color: "#fbbf24 !important",
                            }}
                          />
                        }
                        label={`EV+`}
                        size="small"
                        sx={{
                          height: 20,
                          fontSize: "0.65rem",
                          bgcolor: "rgba(251, 191, 36, 0.15)",
                          color: "#fbbf24",
                          border: "1px solid rgba(251, 191, 36, 0.3)",
                          "& .MuiChip-label": { px: 0.5 },
                        }}
                      />
                    )}
                    <Chip
                      label={`${(item.probability * 100).toFixed(0)}%`}
                      size="small"
                      variant="outlined"
                      sx={{
                        height: 20,
                        fontSize: "0.65rem",
                        color: "#10b981",
                        borderColor: "rgba(16,185,129,0.3)",
                      }}
                    />
                  </Box>
                </Box>
              </ListItem>
            ))}
          </List>

          <Box sx={{ p: 2, bgcolor: "rgba(0,0,0,0.2)" }}>
            <Box
              sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}
            >
              <Typography variant="body2" color="text.secondary">
                Probabilidad Total
              </Typography>
              <Typography variant="body2" color="white">
                {stats.totalProb.toFixed(1)}%
              </Typography>
            </Box>
            <Box
              sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}
            >
              <Typography variant="body2" color="text.secondary">
                Cuota Aprox.
              </Typography>
              <Typography variant="body2" color="#10b981" fontWeight="bold">
                {stats.combinedOdds}
              </Typography>
            </Box>

            <Box sx={{ display: "flex", gap: 1 }}>
              <Button
                variant="outlined"
                color="error"
                size="small"
                fullWidth
                onClick={clearPicks}
                startIcon={<DeleteOutline />}
                sx={{ minHeight: 44 }}
              >
                Limpiar
              </Button>
              {/* Future feature: Save/Share Parley */}
            </Box>
          </Box>
        </Box>
      </Collapse>
    </Paper>
  );
};

export default ParleySlip;

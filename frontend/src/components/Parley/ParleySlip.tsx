import React, { useMemo } from "react";
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
} from "@mui/icons-material";
import { MatchPrediction } from "../../types";

export interface ParleyPickItem {
  match: MatchPrediction;
  pick: string; // '1', 'X', '2'
  probability: number;
  label: string; // e.g. "Local", "Empate", "Visitante"
}

interface ParleySlipProps {
  items: ParleyPickItem[];
  onRemove: (matchId: string) => void;
  onClear: () => void;
  isOpen: boolean;
  onToggle: () => void;
}

const ParleySlip: React.FC<ParleySlipProps> = ({
  items,
  onRemove,
  onClear,
  isOpen,
  onToggle,
}) => {
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

  if (items.length === 0) return null;

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
        bgcolor: "#1e293b",
        border: "1px solid rgba(255,255,255,0.1)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header */}
      <Box
        sx={{
          p: 2,
          bgcolor: "#0f172a",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          cursor: "pointer",
          borderBottom: "1px solid rgba(255,255,255,0.1)",
        }}
        onClick={onToggle}
      >
        <Box sx={{ display: "flex", alignItems: "center" }}>
          <LocalActivity sx={{ color: "#6366f1", mr: 1 }} />
          <Typography variant="subtitle1" fontWeight="bold" color="white">
            Mi Parley
          </Typography>
          <Chip
            label={items.length}
            size="small"
            color="primary"
            sx={{ ml: 1, height: 20, minWidth: 20 }}
          />
        </Box>
        <IconButton size="small" sx={{ color: "text.secondary" }}>
          {isOpen ? <ExpandMore /> : <ExpandLess />}
        </IconButton>
      </Box>

      {/* Content */}
      <Collapse in={isOpen}>
        <Box sx={{ p: 0, maxHeight: 400, overflowY: "auto" }}>
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
                    {item.match.match.home_team.name} vs{" "}
                    {item.match.match.away_team.name}
                  </Typography>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemove(item.match.match.id);
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
                    <Chip
                      label={item.pick}
                      size="small"
                      color="secondary"
                      sx={{ fontWeight: "bold", height: 24, minWidth: 24 }}
                    />
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
                onClick={onClear}
                startIcon={<DeleteOutline />}
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

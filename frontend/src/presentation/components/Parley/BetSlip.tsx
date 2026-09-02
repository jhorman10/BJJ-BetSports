import React from "react";
import {
  Box,
  Typography,
  Chip,
  IconButton,
  List,
  ListItem,
  Divider,
  Button,
  Paper,
} from "@mui/material";
import { LocalActivity, Close, Info } from "@mui/icons-material";

import { getTeamDisplayName } from "../../../utils/teamUtils";
import { MatchPrediction } from "../../../domain/entities";

interface PickItem {
  match: MatchPrediction;
  pick: string;
  label: string;
  probability: number;
}

interface BetSlipProps {
  picks: PickItem[];
  stats: { totalProb: number; combinedOdds: string };
  onRemovePick: (matchId: string) => void;
  onClearPicks: () => void;
}

const BetSlip: React.FC<BetSlipProps> = ({ picks, stats, onRemovePick, onClearPicks }) => (
  <Paper
    sx={{
      p: 3,
      bgcolor: "#1e293b",
      borderRadius: 4,
      elevation: 4,
      border: "1px solid rgba(255,255,255,0.1)",
    }}
  >
    <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
      <Box sx={{ display: "flex", alignItems: "center" }}>
        <LocalActivity sx={{ color: "#6366f1", mr: 1 }} />
        <Typography variant="h6" color="white" fontWeight="bold">Mi Ticket</Typography>
      </Box>
      <Chip label={`${picks.length} Picks`} color="primary" size="small" />
    </Box>

    {picks.length === 0 ? (
      <Box sx={{ py: 6, textAlign: "center", color: "text.secondary" }}>
        <Typography variant="body1">No has añadido picks todavía.</Typography>
        <Typography variant="body2" sx={{ mt: 1 }}>Usa el buscador para armar tu combinación.</Typography>
      </Box>
    ) : (
      <List disablePadding sx={{ mb: 2 }}>
        {picks.map((item, idx) => (
          <React.Fragment key={item.match.match.id}>
            <ListItem sx={{ px: 0, py: 1.5, display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
              <Box sx={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <Typography variant="caption" color="text.secondary">
                  {getTeamDisplayName(item.match.match?.home_team)} vs {getTeamDisplayName(item.match.match?.away_team)}
                </Typography>
                <IconButton size="small" onClick={() => onRemovePick(item.match.match.id)} sx={{ p: 0.5, color: "error.main" }}>
                  <Close fontSize="small" />
                </IconButton>
              </Box>
              <Box sx={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", mt: 0.5 }}>
                <Typography variant="body1" color="white" fontWeight="bold">{item.label}</Typography>
                <Chip
                  label={`${(item.probability * 100).toFixed(1)}%`}
                  size="small"
                  sx={{ height: 24, fontWeight: "bold", bgcolor: "rgba(16,185,129,0.1)", color: "#10b981" }}
                />
              </Box>
            </ListItem>
            {idx < picks.length - 1 && <Divider sx={{ borderColor: "rgba(255,255,255,0.05)" }} />}
          </React.Fragment>
        ))}
      </List>
    )}

    <Box sx={{ bgcolor: "rgba(0,0,0,0.3)", p: 2, borderRadius: 2, mt: 2 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
        <Typography variant="body2" color="text.secondary">Probabilidad Matemática Combinada</Typography>
        <Typography variant="body2" color="white">{stats.totalProb.toFixed(2)}%</Typography>
      </Box>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
        <Typography variant="body2" color="text.secondary">Cuota Justa Aproximada</Typography>
        <Typography variant="body1" color="#10b981" fontWeight="bold">{stats.combinedOdds}</Typography>
      </Box>
      <Box sx={{ display: "flex", gap: 2, mt: 2 }}>
        <Button fullWidth variant="outlined" color="error" onClick={onClearPicks} disabled={picks.length === 0}>
          Limpiar
        </Button>
      </Box>
      <Box sx={{ display: "flex", alignItems: "flex-start", mt: 2, gap: 1 }}>
        <Info sx={{ fontSize: 16, color: "text.secondary", mt: 0.2 }} />
        <Typography variant="caption" color="text.secondary">
          La probabilidad combinada siempre disminuirá al agregar picks. Recomendamos seleccionar picks con alto porcentaje base para amortiguar este efecto y generar valor (EV+).
        </Typography>
      </Box>
    </Box>
  </Paper>
);

export default BetSlip;

import React from "react";
import {
  Box,
  Typography,
  ToggleButton,
  ToggleButtonGroup,
  TextField,
  Grid,
} from "@mui/material";
import { SmartToy, History, CheckCircle, Cancel } from "@mui/icons-material";

import StatCard from "./StatCard";

interface DashboardHeaderProps {
  yearMode: "current" | "previous";
  displayStartDate: string;
  onYearToggle: (
    _event: React.MouseEvent<HTMLElement>,
    newMode: "current" | "previous" | null
  ) => void;
  onStartChange: (date: string) => void;
}

export const DashboardHeader: React.FC<DashboardHeaderProps> = ({
  yearMode,
  displayStartDate,
  onYearToggle,
  onStartChange,
}) => (
  <Box
    display="flex"
    alignItems="center"
    justifyContent="space-between"
    mb={4}
    flexWrap="wrap"
    gap={2}
  >
    <Box display="flex" alignItems="center" gap={2}>
      <SmartToy sx={{ fontSize: 40, color: "#fbbf24" }} />
      <Box>
        <Typography variant="h4" fontWeight={700} color="white">
          Estadísticas del Bot
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Historial de picks y porcentaje de aciertos
        </Typography>
      </Box>
    </Box>
    <Box display="flex" alignItems="center" gap={2}>
      <ToggleButtonGroup
        value={yearMode}
        exclusive
        onChange={onYearToggle}
        size="small"
        sx={{
          bgcolor: "rgba(30, 41, 59, 0.6)",
          "& .MuiToggleButton-root": {
            color: "rgba(255, 255, 255, 0.7)",
            textTransform: "none",
            "&.Mui-selected": {
              color: "#fbbf24",
              bgcolor: "rgba(251, 191, 36, 0.1)",
            },
          },
        }}
      >
        <ToggleButton value="previous">Año Anterior</ToggleButton>
        <ToggleButton value="current">Año Actual</ToggleButton>
      </ToggleButtonGroup>
      <TextField
        label="Desde"
        type="date"
        value={displayStartDate}
        onChange={(e) => onStartChange(e.target.value)}
        InputLabelProps={{ shrink: true }}
        size="small"
        sx={{
          "& .MuiInputBase-root": {
            bgcolor: "rgba(30, 41, 59, 0.6)",
            color: "white",
          },
          "& .MuiInputLabel-root": { color: "rgba(255,255,255,0.7)" },
        }}
      />
    </Box>
  </Box>
);

interface SummaryCardsProps {
  totalPicks: number;
  picksWon: number;
  picksLost: number;
  accuracy: number;
}

export const SummaryCards: React.FC<SummaryCardsProps> = ({
  totalPicks,
  picksWon,
  picksLost,
  accuracy,
}) => (
  <Grid container spacing={3} sx={{ mb: 4 }}>
    <Grid size={{ xs: 12, md: 4 }}>
      <StatCard
        title="Total Picks"
        value={totalPicks.toString()}
        icon={<History />}
        color="#3b82f6"
        subtitle="Picks analizados en el período"
      />
    </Grid>
    <Grid size={{ xs: 12, md: 4 }}>
      <StatCard
        title="Picks Ganados"
        value={`${picksWon} (${accuracy.toFixed(1)}%)`}
        icon={<CheckCircle />}
        color="#22c55e"
        subtitle="Picks acertados"
      />
    </Grid>
    <Grid size={{ xs: 12, md: 4 }}>
      <StatCard
        title="Picks Perdidos"
        value={picksLost.toString()}
        icon={<Cancel />}
        color="#ef4444"
        subtitle="Picks fallados"
      />
    </Grid>
  </Grid>
);

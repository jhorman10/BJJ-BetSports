import React from "react";
import { Box, Typography, Tooltip, Chip } from "@mui/material";
import TrendingUp from "@mui/icons-material/TrendingUp";
import TrendingDown from "@mui/icons-material/TrendingDown";
import Info from "@mui/icons-material/Info";

import type { MatchPrediction } from "../../../types";

interface ProbabilityBarsProps {
  prediction: MatchPrediction["prediction"];
  homeWinPercent: string;
  drawPercent: string;
  awayWinPercent: string;
  homeWinColor: string;
  drawColor: string;
  awayWinColor: string;
}

// Styled probability bar with custom colors
const ProbabilityBar = (props: { value: number; barcolor: string }): React.JSX.Element => (
  <Box
    sx={{
      height: 10,
      borderRadius: 5,
      backgroundColor: "rgba(255, 255, 255, 0.05)",
      overflow: "hidden",
      position: "relative",
    }}
  >
    <Box
      sx={{
        height: "100%",
        width: `${props.value}%`,
        backgroundColor: props.barcolor,
        borderRadius: 5,
      }}
    />
  </Box>
);

interface OverUnderChipsProps {
  prediction: MatchPrediction["prediction"];
  overPercent: string;
  underPercent: string;
}

export const ProbabilityBars: React.FC<ProbabilityBarsProps> = ({
  prediction,
  homeWinPercent,
  drawPercent,
  awayWinPercent,
  homeWinColor,
  drawColor,
  awayWinColor,
}) => (
  <Box mb={3}>
    <Typography variant="subtitle2" color="text.secondary" mb={2}>Probabilidades</Typography>
    <Box mb={1.5}>
      <Box display="flex" justifyContent="space-between" mb={0.5}>
        <Typography variant="body2">Local (1)</Typography>
        <Typography variant="body2" fontWeight={600}>{homeWinPercent}</Typography>
      </Box>
      <ProbabilityBar value={prediction.home_win_probability * 100} barcolor={homeWinColor} />
    </Box>
    <Box mb={1.5}>
      <Box display="flex" justifyContent="space-between" mb={0.5}>
        <Typography variant="body2">Empate (X)</Typography>
        <Typography variant="body2" fontWeight={600}>{drawPercent}</Typography>
      </Box>
      <ProbabilityBar value={prediction.draw_probability * 100} barcolor={drawColor} />
    </Box>
    <Box mb={1.5}>
      <Box display="flex" justifyContent="space-between" mb={0.5}>
        <Typography variant="body2">Visitante (2)</Typography>
        <Typography variant="body2" fontWeight={600}>{awayWinPercent}</Typography>
      </Box>
      <ProbabilityBar value={prediction.away_win_probability * 100} barcolor={awayWinColor} />
    </Box>
  </Box>
);

export const OverUnderChips: React.FC<OverUnderChipsProps> = ({ prediction, overPercent, underPercent }) => (
  <Box mb={2}>
    <Typography variant="subtitle2" color="text.secondary" mb={1}>Más/Menos de 2.5 Goles</Typography>
    <Box display="flex" gap={1}>
      <Chip
        icon={<TrendingUp />}
        label={`Más: ${overPercent}`}
        color={prediction.over_25_probability > 0.5 ? "success" : "default"}
        variant={prediction.over_25_probability > 0.5 ? "filled" : "outlined"}
        size="small"
        sx={{
          color: "#ffffff",
          fontWeight: 700,
          bgcolor: prediction.over_25_probability > 0.5 ? "success.main" : "transparent",
          borderColor: "success.main",
          ...(prediction.over_25_probability > 0.5 && { boxShadow: "0 0 10px rgba(16, 185, 129, 0.4)" }),
        }}
      />
      <Chip
        icon={<TrendingDown />}
        label={`Menos: ${underPercent}`}
        color={prediction.under_25_probability > 0.5 ? "error" : "default"}
        variant={prediction.under_25_probability > 0.5 ? "filled" : "outlined"}
        size="small"
        sx={{
          color: "#ffffff",
          fontWeight: 700,
          bgcolor: prediction.under_25_probability > 0.5 ? "error.main" : "transparent",
          borderColor: "error.main",
          ...(prediction.under_25_probability > 0.5 && { boxShadow: "0 0 10px rgba(239, 68, 68, 0.4)" }),
        }}
      />
    </Box>
  </Box>
);

interface ConfidenceSourcesProps {
  confidencePercent: string;
  sourcesTooltip: string;
  dataSourcesLength: number;
}

export const ConfidenceSources: React.FC<ConfidenceSourcesProps> = ({
  confidencePercent,
  sourcesTooltip,
  dataSourcesLength,
}) => (
  <Box
    display="flex"
    justifyContent="space-between"
    alignItems="center"
    pt={1}
    borderTop="1px solid rgba(255, 255, 255, 0.1)"
  >
    <Tooltip title="Nivel de confianza basado en la cantidad y calidad de datos disponibles">
      <Box display="flex" alignItems="center" gap={1}>
        <Info fontSize="small" color="action" />
        <Typography variant="caption" color="text.secondary">Confianza: {confidencePercent}</Typography>
      </Box>
    </Tooltip>
    <Box display="flex" gap={1} alignItems="center">
      <Tooltip title={sourcesTooltip}>
        <Chip
          label={`${dataSourcesLength} fuentes`}
          size="small"
          variant="outlined"
          sx={{ fontSize: "0.7rem" }}
        />
      </Tooltip>
    </Box>
  </Box>
);

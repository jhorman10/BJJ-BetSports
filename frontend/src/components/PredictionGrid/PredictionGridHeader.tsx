import React from "react";
import {
  Box,
  Typography,
  ToggleButton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
} from "@mui/material";
import { Sort, LiveTv } from "@mui/icons-material";
import { League } from "../../types";

export type SortOption =
  | "confidence"
  | "date"
  | "home_probability"
  | "away_probability";

const sortLabels: Record<SortOption, string> = {
  confidence: "Confianza",
  date: "Fecha",
  home_probability: "Prob. Local",
  away_probability: "Prob. Visitante",
};

interface PredictionGridHeaderProps {
  league: League | null;
  predictionCount: number;
  showLiveOnly: boolean;
  onLiveToggle: () => void;
  sortBy: SortOption;
  onSortChange: (sortBy: SortOption) => void;
}

const PredictionGridHeader: React.FC<PredictionGridHeaderProps> = ({
  league,
  predictionCount,
  showLiveOnly,
  onLiveToggle,
  sortBy,
  onSortChange,
}) => {
  const handleSortChange = (event: SelectChangeEvent<SortOption>) => {
    onSortChange(event.target.value as SortOption);
  };

  return (
    <Box
      display="flex"
      justifyContent="space-between"
      alignItems="center"
      mb={3}
      flexWrap="wrap"
      gap={2}
    >
      {league && (
        <Box>
          <Typography variant="h5" fontWeight={600}>
            Predicciones: {league.name}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {predictionCount} partidos analizados
          </Typography>
        </Box>
      )}

      <Box display="flex" gap={2} flexWrap="wrap" alignItems="center">
        {/* Live Toggle */}
        <ToggleButton
          value="check"
          selected={showLiveOnly}
          onChange={onLiveToggle}
          size="small"
          color="error"
          sx={{ borderRadius: 2 }}
        >
          <LiveTv fontSize="small" sx={{ mr: 1 }} />
          EN VIVO
        </ToggleButton>

        {/* Sort Dropdown */}
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel id="sort-by-label">
            <Box display="flex" alignItems="center" gap={0.5}>
              <Sort fontSize="small" />
              Ordenar por
            </Box>
          </InputLabel>
          <Select
            labelId="sort-by-label"
            value={sortBy}
            label="Ordenar por"
            onChange={handleSortChange}
          >
            {(Object.entries(sortLabels) as [SortOption, string][]).map(
              ([value, label]) => (
                <MenuItem key={value} value={value}>
                  {label}
                </MenuItem>
              )
            )}
          </Select>
        </FormControl>
      </Box>
    </Box>
  );
};

export default PredictionGridHeader;

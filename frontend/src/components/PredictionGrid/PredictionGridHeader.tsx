import React from "react";
import {
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
} from "@mui/material";
import { Sort } from "@mui/icons-material";
import { League } from "../../types";
import { getLeagueName } from "../LeagueSelector/constants";
import TeamSearch from "../TeamSearch/TeamSearch";

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
  sortBy: SortOption;
  onSortChange: (sortBy: SortOption) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

const PredictionGridHeader: React.FC<PredictionGridHeaderProps> = ({
  league,
  predictionCount,
  sortBy,
  onSortChange,
  searchQuery,
  onSearchChange,
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
            Predicciones: {getLeagueName(league.name)}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {predictionCount} partidos analizados
          </Typography>
        </Box>
      )}

      <Box
        display="flex"
        gap={2}
        alignItems="center"
        sx={{ ml: "auto", maxWidth: "100%" }}
      >
        {/* Search Bar */}
        <TeamSearch
          searchQuery={searchQuery}
          onSearchChange={onSearchChange}
          sx={{ flex: 1, minWidth: { xs: 120, sm: 200 }, mr: 1 }}
        />

        {/* Sort Dropdown */}
        <FormControl size="small" sx={{ minWidth: { xs: 120, sm: 150 } }}>
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

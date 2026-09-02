import React from "react";
import {
  Box,
  Typography,
  Autocomplete,
  TextField,
  CircularProgress,
  Grid,
  Button,
} from "@mui/material";

import { usePredictionStore } from "../../../application/stores/usePredictionStore";
import { getTeamDisplayName } from "../../../utils/teamUtils";
import { MatchPrediction } from "../../../domain/entities";

interface MatchSearchSectionProps {
  selectedMatch: MatchPrediction | null;
  onSelectMatch: (match: MatchPrediction | null) => void;
  onAddPick: (match: MatchPrediction, pick: string, label: string, probability: number) => void;
}

const MatchSearchSection: React.FC<MatchSearchSectionProps> = ({
  selectedMatch,
  onSelectMatch,
  onAddPick,
}) => {
  const {
    searchMatches,
    searchLoading,
    setSearchQuery,
    searchQuery,
  } = usePredictionStore();

  const handleSearchChange = (_event: React.SyntheticEvent, value: string): void => {
    setSearchQuery(value);
  };

  const handleMatchSelect = (_event: React.SyntheticEvent, value: MatchPrediction | null): void => {
    onSelectMatch(value);
  };

  return (
    <Box>
      <Autocomplete
        options={(searchMatches || []).filter((m) => m && m.match)}
        getOptionLabel={(option) => {
          if (!option || !option.match) return "";
          return `${getTeamDisplayName(option.match.home_team)} vs ${getTeamDisplayName(option.match.away_team)}`;
        }}
        onInputChange={handleSearchChange}
        inputValue={searchQuery}
        onChange={handleMatchSelect}
        value={selectedMatch}
        loading={searchLoading}
        renderInput={(params) => (
          <TextField
            {...params}
            label="Escribe un equipo o liga..."
            variant="outlined"
            fullWidth
            InputProps={{
              ...params.InputProps,
              endAdornment: (
                <React.Fragment>
                  {searchLoading ? <CircularProgress color="inherit" size={20} /> : null}
                  {params.InputProps.endAdornment}
                </React.Fragment>
              ),
            }}
          />
        )}
      />

      {selectedMatch && (
        <Box sx={{ mt: 3 }}>
          <Typography variant="subtitle1" fontWeight="bold" sx={{ mb: 1 }}>
            Mercados Principales
          </Typography>
          <Grid container spacing={2}>
            {[
              { pick: "1", label: `Local (${getTeamDisplayName(selectedMatch.match?.home_team)})`, prob: selectedMatch.prediction?.home_win_probability || 0, caption: "Local" },
              { pick: "X", label: "Empate", prob: selectedMatch.prediction?.draw_probability || 0, caption: "Empate" },
              { pick: "2", label: `Visitante (${getTeamDisplayName(selectedMatch.match?.away_team)})`, prob: selectedMatch.prediction?.away_win_probability || 0, caption: "Visitante" },
            ].map((item) => (
              <Grid size={{ xs: 12, sm: 4 }} key={item.pick}>
                <Button
                  fullWidth
                  variant="outlined"
                  sx={{ display: "flex", flexDirection: "column", py: 1 }}
                  onClick={() => onAddPick(selectedMatch, item.pick, item.label, item.prob)}
                >
                  <Typography variant="caption">{item.caption}</Typography>
                  <Typography variant="body1" fontWeight="bold">
                    {(item.prob * 100).toFixed(1)}%
                  </Typography>
                </Button>
              </Grid>
            ))}
            {[
              { pick: "OVER_2.5", label: "+2.5 Goles", prob: selectedMatch.prediction?.over_25_probability || 0, caption: "+2.5 Goles" },
              { pick: "UNDER_2.5", label: "-2.5 Goles", prob: selectedMatch.prediction?.under_25_probability || 0, caption: "-2.5 Goles" },
            ].map((item) => (
              <Grid size={{ xs: 12, sm: 6 }} key={item.pick}>
                <Button
                  fullWidth
                  variant="outlined"
                  sx={{ display: "flex", flexDirection: "column", py: 1 }}
                  onClick={() => onAddPick(selectedMatch, item.pick, item.label, item.prob)}
                >
                  <Typography variant="caption">{item.caption}</Typography>
                  <Typography variant="body1" fontWeight="bold">
                    {(item.prob * 100).toFixed(1)}%
                  </Typography>
                </Button>
              </Grid>
            ))}
          </Grid>
        </Box>
      )}
    </Box>
  );
};

export default MatchSearchSection;

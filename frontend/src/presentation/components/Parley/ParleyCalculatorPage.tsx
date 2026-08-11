import React, { useState, useEffect, useMemo } from "react";
import {
  Container,
  Box,
  Typography,
  Paper,
  Autocomplete,
  TextField,
  CircularProgress,
  Grid,
  Button,
  Chip,
  IconButton,
  List,
  ListItem,
  Divider,
} from "@mui/material";
import { Calculate, Close, LocalActivity, Info } from "@mui/icons-material";

import { usePredictionStore } from "../../../application/stores/usePredictionStore";
import { useParleyStore } from "../../../application/stores/useParleyStore";
import { getTeamDisplayName } from "../../../utils/teamUtils";
import { MatchPrediction } from "../../../domain/entities";

import { ParleySuggestions } from "./ParleySuggestions";

const ParleyCalculatorPage: React.FC = () => {
  const {
    searchMatches,
    searchLoading,
    setSearchQuery,
    searchQuery,
  } = usePredictionStore();

  const { selectedPicks, removePick, addPick, clearPicks } = useParleyStore();

  const [selectedMatch, setSelectedMatch] = useState<MatchPrediction | null>(null);

  // Clear search on mount
  useEffect(() => {
    setSearchQuery("");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearchChange = (_event: React.SyntheticEvent, value: string): void => {
    setSearchQuery(value);
  };

  const handleMatchSelect = (_event: React.SyntheticEvent, value: MatchPrediction | null): void => {
    setSelectedMatch(value);
  };

  // Helper to add manual picks from default probabilities
  const handleAddManualPick = (match: MatchPrediction, pick: string, label: string, probability: number): void => {
    addPick(match.match.id, {
      match,
      pick,
      label,
      probability,
    });
    setSelectedMatch(null);
    setSearchQuery("");
  };

  const currentPicks = useMemo(() => Object.values(selectedPicks), [selectedPicks]);

  const stats = useMemo(() => {
    const totalProb = currentPicks.reduce((acc, curr) => acc * curr.probability, 1.0);
    const combinedOdds = totalProb > 0 ? 1 / totalProb : 0;
    return {
      totalProb: totalProb * 100,
      combinedOdds: combinedOdds.toFixed(2),
    };
  }, [currentPicks]);

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4, display: "flex", alignItems: "center" }}>
        <Calculate sx={{ fontSize: 40, color: "primary.main", mr: 2 }} />
        <Box>
          <Typography variant="h4" fontWeight="bold" color="white">
            Calculadora de Parlay
          </Typography>
          <Typography variant="body1" color="text.secondary">
            Arma tu parlay manual, evalúa las probabilidades y encuentra oportunidades de valor.
          </Typography>
        </Box>
      </Box>

      <Grid container spacing={4}>
        {/* Left Column: Search & Add */}
        <Grid size={{ xs: 12, md: 7 }}>
          <Paper sx={{ p: 3, bgcolor: "background.paper", borderRadius: 4, elevation: 3, mb: 3 }}>
            <Typography variant="h6" fontWeight="bold" sx={{ mb: 2 }}>
              Buscar Partido
            </Typography>
            <Autocomplete
              options={(searchMatches || []).filter(m => m && m.match)}
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

            {/* Manual Pick Selector for Selected Match */}
            {selectedMatch && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle1" fontWeight="bold" sx={{ mb: 1 }}>
                  Mercados Principales
                </Typography>
                <Grid container spacing={2}>
                  <Grid size={{ xs: 12, sm: 4 }}>
                    <Button
                      fullWidth
                      variant="outlined"
                      sx={{ display: 'flex', flexDirection: 'column', py: 1 }}
                      onClick={() =>
                        handleAddManualPick(
                          selectedMatch,
                          "1",
                          `Local (${getTeamDisplayName(selectedMatch.match?.home_team)})`,
                          selectedMatch.prediction?.home_win_probability || 0
                        )
                      }
                    >
                      <Typography variant="caption">Local</Typography>
                      <Typography variant="body1" fontWeight="bold">
                        {((selectedMatch.prediction?.home_win_probability || 0) * 100).toFixed(1)}%
                      </Typography>
                    </Button>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 4 }}>
                    <Button
                      fullWidth
                      variant="outlined"
                      sx={{ display: 'flex', flexDirection: 'column', py: 1 }}
                      onClick={() =>
                        handleAddManualPick(
                          selectedMatch,
                          "X",
                          "Empate",
                          selectedMatch.prediction?.draw_probability || 0
                        )
                      }
                    >
                      <Typography variant="caption">Empate</Typography>
                      <Typography variant="body1" fontWeight="bold">
                        {((selectedMatch.prediction?.draw_probability || 0) * 100).toFixed(1)}%
                      </Typography>
                    </Button>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 4 }}>
                    <Button
                      fullWidth
                      variant="outlined"
                      sx={{ display: 'flex', flexDirection: 'column', py: 1 }}
                      onClick={() =>
                        handleAddManualPick(
                          selectedMatch,
                          "2",
                          `Visitante (${getTeamDisplayName(selectedMatch.match?.away_team)})`,
                          selectedMatch.prediction?.away_win_probability || 0
                        )
                      }
                    >
                      <Typography variant="caption">Visitante</Typography>
                      <Typography variant="body1" fontWeight="bold">
                        {((selectedMatch.prediction?.away_win_probability || 0) * 100).toFixed(1)}%
                      </Typography>
                    </Button>
                  </Grid>

                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Button
                      fullWidth
                      variant="outlined"
                      sx={{ display: 'flex', flexDirection: 'column', py: 1 }}
                      onClick={() =>
                        handleAddManualPick(
                          selectedMatch,
                          "OVER_2.5",
                          "+2.5 Goles",
                          selectedMatch.prediction?.over_25_probability || 0
                        )
                      }
                    >
                      <Typography variant="caption">+2.5 Goles</Typography>
                      <Typography variant="body1" fontWeight="bold">
                        {((selectedMatch.prediction?.over_25_probability || 0) * 100).toFixed(1)}%
                      </Typography>
                    </Button>
                  </Grid>
                  <Grid size={{ xs: 12, sm: 6 }}>
                    <Button
                      fullWidth
                      variant="outlined"
                      sx={{ display: 'flex', flexDirection: 'column', py: 1 }}
                      onClick={() =>
                        handleAddManualPick(
                          selectedMatch,
                          "UNDER_2.5",
                          "-2.5 Goles",
                          selectedMatch.prediction?.under_25_probability || 0
                        )
                      }
                    >
                      <Typography variant="caption">-2.5 Goles</Typography>
                      <Typography variant="body1" fontWeight="bold">
                        {((selectedMatch.prediction?.under_25_probability || 0) * 100).toFixed(1)}%
                      </Typography>
                    </Button>
                  </Grid>
                </Grid>
              </Box>
            )}

            {/* Sugerencias Automatizadas del Store */}
            <ParleySuggestions />
          </Paper>
        </Grid>

        {/* Right Column: Ticket / Summary */}
        <Grid size={{ xs: 12, md: 5 }}>
          <Paper
            sx={{
              p: 3,
              bgcolor: "#1e293b", // Slate 800
              borderRadius: 4,
              elevation: 4,
              border: "1px solid rgba(255,255,255,0.1)",
            }}
          >
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 2 }}>
              <Box sx={{ display: "flex", alignItems: "center" }}>
                <LocalActivity sx={{ color: "#6366f1", mr: 1 }} />
                <Typography variant="h6" color="white" fontWeight="bold">
                  Mi Ticket
                </Typography>
              </Box>
              <Chip label={`${currentPicks.length} Picks`} color="primary" size="small" />
            </Box>

            {currentPicks.length === 0 ? (
              <Box sx={{ py: 6, textAlign: "center", color: "text.secondary" }}>
                <Typography variant="body1">No has añadido picks todavía.</Typography>
                <Typography variant="body2" sx={{ mt: 1 }}>
                  Usa el buscador para armar tu combinación.
                </Typography>
              </Box>
            ) : (
              <List disablePadding sx={{ mb: 2 }}>
                {currentPicks.map((item, idx) => (
                  <React.Fragment key={item.match.match?.id || idx}>
                    <ListItem sx={{ px: 0, py: 1.5, display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
                      <Box sx={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <Typography variant="caption" color="text.secondary">
                          {getTeamDisplayName(item.match.match?.home_team)} vs {getTeamDisplayName(item.match.match?.away_team)}
                        </Typography>
                        <IconButton
                          size="small"
                          onClick={() => removePick(item.match.match.id)}
                          sx={{ p: 0.5, color: "error.main" }}
                        >
                          <Close fontSize="small" />
                        </IconButton>
                      </Box>
                      <Box sx={{ width: "100%", display: "flex", justifyContent: "space-between", alignItems: "center", mt: 0.5 }}>
                        <Typography variant="body1" color="white" fontWeight="bold">
                          {item.label}
                        </Typography>
                        <Chip
                          label={`${(item.probability * 100).toFixed(1)}%`}
                          size="small"
                          sx={{ height: 24, fontWeight: "bold", bgcolor: "rgba(16,185,129,0.1)", color: "#10b981" }}
                        />
                      </Box>
                    </ListItem>
                    {idx < currentPicks.length - 1 && <Divider sx={{ borderColor: "rgba(255,255,255,0.05)" }} />}
                  </React.Fragment>
                ))}
              </List>
            )}

            <Box sx={{ bgcolor: "rgba(0,0,0,0.3)", p: 2, borderRadius: 2, mt: 2 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", mb: 1 }}>
                <Typography variant="body2" color="text.secondary">
                  Probabilidad Matemática Combinada
                </Typography>
                <Typography variant="body2" color="white">
                  {stats.totalProb.toFixed(2)}%
                </Typography>
              </Box>
              <Box sx={{ display: "flex", justifyContent: "space-between", mb: 2 }}>
                <Typography variant="body2" color="text.secondary">
                  Cuota Justa Aproximada
                </Typography>
                <Typography variant="body1" color="#10b981" fontWeight="bold">
                  {stats.combinedOdds}
                </Typography>
              </Box>

              <Box sx={{ display: "flex", gap: 2, mt: 2 }}>
                <Button
                  fullWidth
                  variant="outlined"
                  color="error"
                  onClick={clearPicks}
                  disabled={currentPicks.length === 0}
                >
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
        </Grid>
      </Grid>
    </Container>
  );
};

export default ParleyCalculatorPage;

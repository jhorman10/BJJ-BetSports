import React, { useState, useEffect, useMemo } from "react";
import {
  Container,
  Box,
  Typography,
  Paper,
  Grid,
} from "@mui/material";
import { Calculate } from "@mui/icons-material";

import { usePredictionStore } from "../../../application/stores/usePredictionStore";
import { useParleyStore } from "../../../application/stores/useParleyStore";
import { MatchPrediction } from "../../../domain/entities";

import { ParleySuggestions } from "./ParleySuggestions";
import MatchSearchSection from "./MatchSearchSection";
import BetSlip from "./BetSlip";

const ParleyCalculatorPage: React.FC = () => {
  const { setSearchQuery } = usePredictionStore();
  const { selectedPicks, removePick, addPick, clearPicks } = useParleyStore();
  const [selectedMatch, setSelectedMatch] = useState<MatchPrediction | null>(null);

  useEffect(() => {
    setSearchQuery("");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleAddManualPick = (match: MatchPrediction, pick: string, label: string, probability: number): void => {
    addPick(match.match.id, { match, pick, label, probability });
    setSelectedMatch(null);
    setSearchQuery("");
  };

  const currentPicks = useMemo(() => Object.values(selectedPicks), [selectedPicks]);

  const stats = useMemo(() => {
    const totalProb = currentPicks.reduce((acc, curr) => acc * curr.probability, 1.0);
    const combinedOdds = totalProb > 0 ? 1 / totalProb : 0;
    return { totalProb: totalProb * 100, combinedOdds: combinedOdds.toFixed(2) };
  }, [currentPicks]);

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4, display: "flex", alignItems: "center" }}>
        <Calculate sx={{ fontSize: 40, color: "primary.main", mr: 2 }} />
        <Box>
          <Typography variant="h4" fontWeight="bold" color="white">Calculadora de Parlay</Typography>
          <Typography variant="body1" color="text.secondary">
            Arma tu parlay manual, evalúa las probabilidades y encuentra oportunidades de valor.
          </Typography>
        </Box>
      </Box>

      <Grid container spacing={4}>
        <Grid size={{ xs: 12, md: 7 }}>
          <Paper sx={{ p: 3, bgcolor: "background.paper", borderRadius: 4, elevation: 3, mb: 3 }}>
            <Typography variant="h6" fontWeight="bold" sx={{ mb: 2 }}>Buscar Partido</Typography>
            <MatchSearchSection
              selectedMatch={selectedMatch}
              onSelectMatch={setSelectedMatch}
              onAddPick={handleAddManualPick}
            />
            <ParleySuggestions />
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 5 }}>
          <BetSlip
            picks={currentPicks}
            stats={stats}
            onRemovePick={removePick}
            onClearPicks={clearPicks}
          />
        </Grid>
      </Grid>
    </Container>
  );
};

export default ParleyCalculatorPage;

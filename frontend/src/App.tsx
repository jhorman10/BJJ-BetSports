/**
 * Main Application Component
 *
 * Football Betting Prediction Bot - Frontend
 */

import React, { useState } from "react";
import {
  Container,
  Box,
  Typography,
  AppBar,
  Toolbar,
  Alert,
} from "@mui/material";
import { SportsSoccer } from "@mui/icons-material";
import LeagueSelector from "./components/LeagueSelector";
import PredictionGrid from "./components/PredictionGrid";
import TeamSearch from "./components/TeamSearch/TeamSearch";
import LiveMatches from "./components/LiveMatches/LiveMatches";
import {
  useLeagues,
  usePredictions,
  useLeagueSelection,
} from "./hooks/usePredictions";

// Sort options type
type SortOption =
  | "confidence"
  | "date"
  | "home_probability"
  | "away_probability";

const App: React.FC = () => {
  // State and data hooks
  const {
    countries,
    loading: leaguesLoading,
    error: leaguesError,
  } = useLeagues();
  const { selectedCountry, selectedLeague, selectCountry, selectLeague } =
    useLeagueSelection();

  // Sorting state
  const [sortBy, setSortBy] = useState<SortOption>("confidence");
  // Search state
  const [searchQuery, setSearchQuery] = useState<string>("");

  const {
    predictions,
    league,
    loading: predictionsLoading,
    error: predictionsError,
  } = usePredictions(selectedLeague?.id || null, 10, sortBy, true);

  // Handle sort change - this automatically triggers refetch via hook dependency
  const handleSortChange = (newSortBy: SortOption) => {
    setSortBy(newSortBy);
  };

  return (
    <Box
      sx={{
        minHeight: "100vh",
        background: "linear-gradient(180deg, #0f172a 0%, #1e293b 100%)",
      }}
    >
      {/* Navigation */}
      <AppBar
        position="static"
        elevation={0}
        sx={{
          background: "transparent",
          borderBottom: "1px solid rgba(148, 163, 184, 0.1)",
        }}
      >
        <Toolbar>
          <SportsSoccer sx={{ mr: 2, color: "primary.main" }} />
          <Typography
            variant="h6"
            component="h1"
            sx={{ flexGrow: 1, fontWeight: 700 }}
          >
            BJJ - BetSports
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Main Content */}
      <Container maxWidth="xl" sx={{ py: 4 }}>
        {/* Header */}
        <Box mb={4}>
          <Typography
            variant="h3"
            fontWeight={700}
            sx={{
              background: "linear-gradient(90deg, #6366f1 0%, #10b981 100%)",
              backgroundClip: "text",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              mb: 1,
            }}
          >
            Predicciones de Fútbol
          </Typography>
          <Typography variant="body1" color="text.secondary" maxWidth={600}>
            Análisis estadístico de partidos de fútbol basado en datos
            históricos, distribución de Poisson y algoritmos de machine
            learning.
          </Typography>
        </Box>

        {/* League Selector */}
        {leaguesError ? (
          <Alert severity="error" sx={{ mb: 4 }}>
            Error al cargar las ligas: {leaguesError.message}
          </Alert>
        ) : (
          <LeagueSelector
            countries={countries}
            selectedCountry={selectedCountry}
            selectedLeague={selectedLeague}
            onCountryChange={selectCountry}
            onLeagueChange={selectLeague}
            loading={leaguesLoading}
          />
        )}

        {/* Search */}
        <Box mb={4}>
          <TeamSearch
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
          />
        </Box>

        {/* Global Live Matches */}
        <Box mb={4}>
          <LiveMatches />
        </Box>

        {/* Predictions Grid */}
        {selectedLeague && (
          <PredictionGrid
            predictions={predictions}
            league={league}
            loading={predictionsLoading}
            error={predictionsError}
            sortBy={sortBy}
            onSortChange={handleSortChange}
            searchQuery={searchQuery}
          />
        )}

        {/* Footer */}
        <Box
          component="footer"
          sx={{
            mt: 8,
            pt: 4,
            borderTop: "1px solid rgba(148, 163, 184, 0.1)",
            textAlign: "center",
          }}
        >
          <Typography variant="body2" color="text.secondary">
            Datos de Football-Data.co.uk, API-Football y Football-Data.org
          </Typography>
          <Typography
            variant="caption"
            color="text.disabled"
            display="block"
            mt={1}
          >
            © 2024 BJJ - BetSports
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

export default App;

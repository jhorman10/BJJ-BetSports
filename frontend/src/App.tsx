/**
 * Main Application Component
 *
 * Football Betting Prediction Bot - Frontend
 */

import React, { useState, useEffect } from "react";
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
import api from "./services/api";
import { MatchPrediction, Country } from "./types";
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
    loading: predictionsLoading,
    error: predictionsError,
  } = usePredictions(selectedLeague?.id || null, 10, sortBy, true);

  // Handle sort change - this automatically triggers refetch via hook dependency
  const handleSortChange = (newSortBy: SortOption) => {
    setSortBy(newSortBy);
  };

  // State for Global/All mode
  const [isGlobalMode, setIsGlobalMode] = useState(false);
  const [dailyMatches, setDailyMatches] = useState<MatchPrediction[]>([]);
  const [dailyLoading, setDailyLoading] = useState(false);

  // Fetch daily matches when Global mode is active
  useEffect(() => {
    if (isGlobalMode) {
      const fetchDaily = async () => {
        setDailyLoading(true);
        try {
          const matches = await api.getDailyMatches();
          // Wrap in MatchPrediction structure
          const predictions: MatchPrediction[] = matches.map((m) => ({
            match: m,
            prediction: {
              match_id: m.id,
              confidence: 0,
              home_win_probability: 0,
              draw_probability: 0,
              away_win_probability: 0,
              over_25_probability: 0,
              under_25_probability: 0,
              predicted_home_goals: 0,
              predicted_away_goals: 0,
              recommended_bet: "N/A",
              over_under_recommendation: "N/A",
              data_sources: [],
              created_at: new Date().toISOString(),
            },
          }));
          setDailyMatches(predictions);
        } catch (e) {
          console.error(e);
        } finally {
          setDailyLoading(false);
        }
      };
      fetchDaily();
    }
  }, [isGlobalMode]);

  const handleCountrySelect = (country: Country | null) => {
    if (country?.name === "Global") {
      setIsGlobalMode(true);
      selectCountry(country);
      selectLeague(null);
    } else {
      setIsGlobalMode(false);
      selectCountry(country);
      selectLeague(null);
    }
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
        <Box mb={4}>
          <TeamSearch
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
          />
        </Box>

        {leaguesError ? (
          <Alert severity="error" sx={{ mb: 4 }}>
            Error al cargar las ligas: {leaguesError.message}
          </Alert>
        ) : (
          <LeagueSelector
            countries={countries}
            selectedCountry={selectedCountry}
            selectedLeague={selectedLeague}
            onCountryChange={handleCountrySelect}
            onLeagueChange={selectLeague}
            loading={leaguesLoading}
          />
        )}

        {/* Global Live Matches */}
        <Box mb={4}>
          <LiveMatches />
        </Box>

        {/* Predictions Grid */}
        {(selectedLeague || isGlobalMode) && (
          <PredictionGrid
            predictions={isGlobalMode ? dailyMatches : predictions}
            league={selectedLeague}
            loading={isGlobalMode ? dailyLoading : predictionsLoading}
            error={isGlobalMode ? null : predictionsError}
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

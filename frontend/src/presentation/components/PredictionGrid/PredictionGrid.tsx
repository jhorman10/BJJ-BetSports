import React, { memo, useMemo, useCallback } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  Alert,
  Snackbar,
} from "@mui/material";
import { SportsSoccer } from "@mui/icons-material";
import type { MatchPrediction } from "../../../types";
import PredictionGridHeader from "./PredictionGridHeader";
import MatchDetailsModal from "../MatchDetails/MatchDetailsModal";
import PredictionGridList, { MatchCardSkeleton } from "./PredictionGridList";
import { getBestPick } from "../../../utils/predictionUtils";
import { isSearchMatch } from "../../../utils/searchUtils";
import { ParleyPickItem } from "../../../application/stores/useParleyStore";

import { usePredictionStore } from "../../../application/stores/usePredictionStore";
import { useParleyStore } from "../../../application/stores/useParleyStore";
import { useOfflineStore } from "../../../application/stores/useOfflineStore";

const emptyStateStyles = {
  border: "2px dashed rgba(148, 163, 184, 0.2)",
  borderRadius: 2,
} as const;

const PredictionGrid: React.FC = memo(() => {
  // Access Store
  const {
    predictions,
    selectedLeague: league,
    predictionsLoading,
    searchLoading,
    predictionsError,
    sortBy,
    setSortBy,
    searchQuery,
    setSearchQuery,
    searchMatches,
    fetchPredictions,
  } = usePredictionStore();

  const { selectedPicks, addPick, removePick } = useParleyStore();
  const { isBackendAvailable } = useOfflineStore();

  // Local state for modal
  const [selectedMatch, setSelectedMatch] =
    React.useState<MatchPrediction | null>(null);
  const [modalOpen, setModalOpen] = React.useState(false);

  // Snackbar state for limits
  const [snackbarOpen, setSnackbarOpen] = React.useState(false);
  const [snackbarMessage, setSnackbarMessage] = React.useState("");

  // Loading state for individual picks
  const [loadingPicks, setLoadingPicks] = React.useState<Set<string>>(
    new Set()
  );

  const handleCloseSnackbar = (
    _event?: React.SyntheticEvent | Event,
    reason?: string
  ) => {
    if (reason === "clickaway") {
      return;
    }
    setSnackbarOpen(false);
  };

  // Fetch predictions when selected league changes
  React.useEffect(() => {
    if (league) {
      fetchPredictions();
    }
  }, [league, fetchPredictions]);

  // Determine which set of predictions to use
  // If searching globally (matched logic in App.tsx typically was > 2 chars)
  const isGlobalSearch = searchQuery.length > 2;

  const loading = isGlobalSearch ? searchLoading : predictionsLoading;
  const error = predictionsError ? new Error(predictionsError) : null;

  const handleMatchClick = useCallback((matchPrediction: MatchPrediction) => {
    setSelectedMatch(matchPrediction);
    setModalOpen(true);
  }, []);

  const handleToggleSelection = useCallback(
    async (match: MatchPrediction) => {
      const matchId = match.match.id;
      const isSelected = !!selectedPicks[matchId];

      if (isSelected) {
        removePick(matchId);
      } else {
        if (Object.keys(selectedPicks).length >= 10) {
          setSnackbarMessage("No puedes agregar más de 10 picks al parley.");
          setSnackbarOpen(true);
          return;
        }

        // Set loading state for this match
        setLoadingPicks((prev) => new Set(prev).add(matchId));

        try {
          // Fetch picks from backend API (same source as modal)
          const { predictionsApi } = await import(
            "../../../infrastructure/api/predictions"
          );
          const apiPicks = await predictionsApi.getSuggestedPicks(matchId);

          let picks = apiPicks?.suggested_picks || [];

          // If no API picks, fallback to generated picks
          if (picks.length === 0) {
            picks = getBestPick(match) ? [getBestPick(match)!] : [];
          }

          // Sort by probability and get the best one
          if (picks.length > 0) {
            const bestPick = picks.sort(
              (a, b) => b.probability - a.probability
            )[0];
            const pickItem: ParleyPickItem = {
              match: match,
              pick: bestPick.pick_code || "?",
              probability: bestPick.probability,
              label: bestPick.market_label,
            };
            addPick(matchId, pickItem);
          }
        } catch (error) {
          // Fallback to local generation if API fails
          const bestPick = getBestPick(match);
          if (bestPick) {
            const pickItem: ParleyPickItem = {
              match: match,
              pick: bestPick.pick_code || "?",
              probability: bestPick.probability,
              label: bestPick.market_label,
            };
            addPick(matchId, pickItem);
          }
        } finally {
          // Remove loading state
          setLoadingPicks((prev) => {
            const next = new Set(prev);
            next.delete(matchId);
            return next;
          });
        }
      }
    },
    [selectedPicks, addPick, removePick]
  );

  const handleCloseModal = useCallback(() => {
    setModalOpen(false);
    setSelectedMatch(null);
  }, []);

  // Sort predictions client-side to ensure visual consistency
  const sortedPredictions = useMemo(() => {
    // Start with local league predictions
    let combined = predictions.filter((p) => {
      if (!searchQuery) return true;
      // Check home and away teams
      return (
        isSearchMatch(searchQuery, p.match.home_team.name) ||
        isSearchMatch(searchQuery, p.match.away_team.name)
      );
    });

    // 2. Add Global Search Results (if searching and they aren't already included)
    if (isGlobalSearch && searchMatches.length > 0) {
      const existingIds = new Set(combined.map((p) => p.match.id));
      const newMatches = searchMatches.filter(
        (p) => !existingIds.has(p.match.id)
      );
      combined = [...combined, ...newMatches];
    }

    // 3. Sort the combined list
    return combined.sort((a, b) => {
      switch (sortBy) {
        case "confidence":
          return b.prediction.confidence - a.prediction.confidence;
        case "date":
          return (
            new Date(a.match.match_date).getTime() -
            new Date(b.match.match_date).getTime()
          );
        case "home_probability":
          return (
            b.prediction.home_win_probability -
            a.prediction.home_win_probability
          );
        case "away_probability":
          return (
            b.prediction.away_win_probability -
            a.prediction.away_win_probability
          );
        default:
          return 0;
      }
    });
  }, [predictions, searchMatches, searchQuery, isGlobalSearch, sortBy]);

  // Persistent Header with Conditional Content Below
  return (
    <Box>
      <PredictionGridHeader
        league={league}
        predictionCount={sortedPredictions.length}
        sortBy={sortBy}
        onSortChange={setSortBy}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
      />

      {loading ? (
        <Box>
          <Box display="flex" alignItems="center" gap={2} mb={3}>
            <CircularProgress size={24} />
            <Typography color="text.secondary">
              Cargando predicciones...
            </Typography>
          </Box>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                sm: "1fr 1fr",
                lg: "1fr 1fr 1fr",
              },
              gap: 3,
            }}
          >
            {[...Array(6)].map((_, index) => (
              <Box key={index}>
                <MatchCardSkeleton />
              </Box>
            ))}
          </Box>
        </Box>
      ) : error && isBackendAvailable ? (
        <Alert severity="error" sx={{ mb: 3 }}>
          Error al cargar predicciones: {error.message}
        </Alert>
      ) : error && !isBackendAvailable ? null : sortedPredictions.length === // Hide local error if backend is globally marked as down
        0 ? (
        <Box
          display="flex"
          flexDirection="column"
          alignItems="center"
          justifyContent="center"
          py={8}
          gap={2}
          sx={emptyStateStyles}
        >
          <SportsSoccer sx={{ fontSize: 64, color: "text.disabled" }} />
          <Typography variant="h6" color="text.secondary">
            {searchQuery.length > 0
              ? "No se encontraron partidos"
              : "No hay predicciones disponibles"}
          </Typography>
          <Typography
            variant="body2"
            color="text.disabled"
            textAlign="center"
            maxWidth={400}
          >
            {searchQuery.length > 0
              ? `No encontramos resultados para "${searchQuery}"`
              : "Selecciona un país y una liga para ver las predicciones de los próximos partidos."}
          </Typography>
        </Box>
      ) : (
        <PredictionGridList
          predictions={sortedPredictions}
          onMatchClick={handleMatchClick}
          selectedMatchIds={Object.keys(selectedPicks)}
          loadingMatchIds={loadingPicks}
          onToggleMatchSelection={handleToggleSelection}
        />
      )}

      {/* Modal */}
      <React.Suspense fallback={null}>
        <MatchDetailsModal
          open={modalOpen}
          onClose={handleCloseModal}
          matchPrediction={selectedMatch}
        />
      </React.Suspense>

      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity="warning"
          sx={{ width: "100%" }}
        >
          {snackbarMessage}
        </Alert>
      </Snackbar>
    </Box>
  );
});

PredictionGrid.displayName = "PredictionGrid";

export default PredictionGrid;

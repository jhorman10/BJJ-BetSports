import React, { memo, useMemo, Suspense, lazy, useCallback } from "react";
import { Box, Typography, CircularProgress, Alert } from "@mui/material";
import { SportsSoccer } from "@mui/icons-material";
import type { MatchPrediction, League } from "../../types";
import PredictionGridHeader, { SortOption } from "./PredictionGridHeader";
import PredictionGridList, { MatchCardSkeleton } from "./PredictionGridList";

const MatchDetailsModal = lazy(
  () => import("../MatchDetails/MatchDetailsModal")
);

interface PredictionGridProps {
  predictions: MatchPrediction[];
  league: League | null;
  loading: boolean;
  error: Error | null;
  sortBy: SortOption;
  onSortChange: (sortBy: SortOption) => void;

  searchQuery: string;
  onSearchChange: (query: string) => void;

  selectedMatchIds?: string[];
  onToggleMatchSelection?: (match: MatchPrediction) => void;
}

const emptyStateStyles = {
  border: "2px dashed rgba(148, 163, 184, 0.2)",
  borderRadius: 2,
} as const;

const PredictionGrid: React.FC<PredictionGridProps> = memo(
  ({
    predictions,
    league,
    loading,
    error,
    sortBy,
    onSortChange,

    searchQuery,
    onSearchChange,
    selectedMatchIds = [],
    onToggleMatchSelection,
  }) => {
    const [selectedMatch, setSelectedMatch] =
      React.useState<MatchPrediction | null>(null);
    const [modalOpen, setModalOpen] = React.useState(false);

    // Filter predictions based on search and live status
    const filteredPredictions = useMemo(() => {
      // If we are showing live only, filtered list is handled by LiveMatchesList component mostly,
      // but for the 'grid' view logic below, we might want to know if there are matches.
      // However, LiveMatchesList fetches its own data.

      // Filter the PROPS predictions (standard predictions)
      return predictions.filter((p) => {
        const matchesSearch =
          searchQuery === "" ||
          p.match.home_team.name
            .toLowerCase()
            .includes(searchQuery.toLowerCase()) ||
          p.match.away_team.name
            .toLowerCase()
            .includes(searchQuery.toLowerCase());

        // Note: 'Live Only' now toggles the view to the LiveMatchesList component
        // which fetches its own real-time data.
        // We ensure we don't double filter if the user just wants to see the grid but searched.
        return matchesSearch;
      });
    }, [predictions, searchQuery]);

    const handleMatchClick = useCallback((matchPrediction: MatchPrediction) => {
      setSelectedMatch(matchPrediction);
      setModalOpen(true);
    }, []);

    const handleCloseModal = useCallback(() => {
      setModalOpen(false);
      setSelectedMatch(null);
    }, []);

    // Sort predictions client-side to ensure visual consistency
    const sortedPredictions = useMemo(() => {
      const sorted = [...filteredPredictions];

      return sorted.sort((a, b) => {
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
    }, [filteredPredictions, sortBy]);

    // Loading state
    if (loading) {
      return (
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
      );
    }

    // Error state
    if (error) {
      return (
        <Alert severity="error">
          Error al cargar predicciones: {error.message}
        </Alert>
      );
    }

    // Empty state (only if not searching/filtering live)
    if (predictions.length === 0 && !loading && !searchQuery) {
      return (
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
            No hay predicciones disponibles
          </Typography>
          <Typography
            variant="body2"
            color="text.disabled"
            textAlign="center"
            maxWidth={400}
          >
            Selecciona un país y una liga para ver las predicciones de los
            próximos partidos.
          </Typography>
        </Box>
      );
    }

    return (
      <Box>
        <PredictionGridHeader
          league={league}
          predictionCount={predictions.length}
          sortBy={sortBy}
          onSortChange={onSortChange}
          searchQuery={searchQuery}
          onSearchChange={onSearchChange}
        />

        <PredictionGridList
          predictions={sortedPredictions}
          onMatchClick={handleMatchClick}
          selectedMatchIds={selectedMatchIds}
          onToggleMatchSelection={onToggleMatchSelection}
        />

        {/* Modal */}
        <Suspense fallback={null}>
          <MatchDetailsModal
            open={modalOpen}
            onClose={handleCloseModal}
            matchPrediction={selectedMatch}
          />
        </Suspense>
      </Box>
    );
  }
);

PredictionGrid.displayName = "PredictionGrid";

export default PredictionGrid;

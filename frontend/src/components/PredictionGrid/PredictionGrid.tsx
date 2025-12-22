/**
 * PredictionGrid Component
 *
 * Grid layout for displaying multiple match predictions.
 * Optimized with React.memo and lazy loading.
 */

import React, { memo, useMemo, Suspense, lazy, useCallback } from "react";
import {
  Grid,
  Box,
  Typography,
  CircularProgress,
  Alert,
  Skeleton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  ToggleButton,
} from "@mui/material";
import { SportsSoccer, Sort, LiveTv } from "@mui/icons-material";
import type { MatchPrediction, League } from "../../types";

// Lazy load MatchCard for better initial load performance
// Lazy load MatchCard and Modal for better initial load performance
const MatchCard = lazy(() => import("../MatchCard"));
const MatchDetailsModal = lazy(
  () => import("../MatchDetails/MatchDetailsModal")
);
const LiveMatchesList = lazy(() => import("../MatchDetails/LiveMatchesList"));

// Sort options type
type SortOption =
  | "confidence"
  | "date"
  | "home_probability"
  | "away_probability";

interface PredictionGridProps {
  predictions: MatchPrediction[];
  league: League | null;
  loading: boolean;
  error: Error | null;
  sortBy: SortOption;
  onSortChange: (sortBy: SortOption) => void;
  searchQuery: string;
  onLiveToggle?: (isLive: boolean) => void;
}

// Sort option labels in Spanish
const sortLabels: Record<SortOption, string> = {
  confidence: "Confianza",
  date: "Fecha",
  home_probability: "Prob. Local",
  away_probability: "Prob. Visitante",
};

// Skeleton component for loading states
const MatchCardSkeleton: React.FC = memo(() => (
  <Box
    sx={{
      p: 3,
      borderRadius: 2,
      bgcolor: "rgba(30, 41, 59, 0.5)",
      border: "1px solid rgba(148, 163, 184, 0.1)",
    }}
  >
    <Skeleton variant="text" width="40%" height={20} sx={{ mb: 2 }} />
    <Skeleton variant="text" width="80%" height={28} sx={{ mb: 1 }} />
    <Skeleton
      variant="rectangular"
      height={60}
      sx={{ mb: 2, borderRadius: 1 }}
    />
    <Skeleton variant="text" width="100%" height={16} sx={{ mb: 1 }} />
    <Skeleton variant="text" width="100%" height={16} sx={{ mb: 1 }} />
    <Skeleton variant="text" width="100%" height={16} sx={{ mb: 2 }} />
    <Box display="flex" gap={1}>
      <Skeleton variant="rounded" width={80} height={24} />
      <Skeleton variant="rounded" width={80} height={24} />
    </Box>
  </Box>
));

MatchCardSkeleton.displayName = "MatchCardSkeleton";

// Empty state styles - defined outside component
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
    onLiveToggle,
  }) => {
    // Local state for UI filters
    const [showLiveOnly, setShowLiveOnly] = React.useState(false);
    const [selectedMatch, setSelectedMatch] =
      React.useState<MatchPrediction | null>(null);
    const [modalOpen, setModalOpen] = React.useState(false);

    // Handle sort change - triggers API refetch via parent
    const handleSortChange = useCallback(
      (event: SelectChangeEvent<SortOption>) => {
        onSortChange(event.target.value as SortOption);
      },
      [onSortChange]
    );

    // Filter predictions based on search and live status
    const filteredPredictions = useMemo(() => {
      return predictions.filter((p) => {
        const matchesSearch =
          searchQuery === "" ||
          p.match.home_team.name
            .toLowerCase()
            .includes(searchQuery.toLowerCase()) ||
          p.match.away_team.name
            .toLowerCase()
            .includes(searchQuery.toLowerCase());

        const isLive = ["1H", "2H", "HT", "LIVE", "ET", "P"].includes(
          p.match.status
        );
        const matchesLive = !showLiveOnly || isLive;

        return matchesSearch && matchesLive;
      });
    }, [predictions, searchQuery, showLiveOnly]);

    const handleMatchClick = useCallback((matchPrediction: MatchPrediction) => {
      setSelectedMatch(matchPrediction);
      setModalOpen(true);
    }, []);

    const handleCloseModal = useCallback(() => {
      setModalOpen(false);
      setSelectedMatch(null);
    }, []);

    // Stable handler for live toggle
    const handleLiveToggle = useCallback(() => {
      setShowLiveOnly((prev) => {
        const newState = !prev;
        if (onLiveToggle) onLiveToggle(newState);
        return newState;
      });
    }, [onLiveToggle]);

    // Memoize the prediction count text
    const predictionCountText = useMemo(
      () => `${predictions.length} partidos analizados`,
      [predictions.length]
    );

    // Sort predictions client-side to ensure visual consistency
    // This runs efficiently on the small dataset (limit=10) and guarantees correct order
    // regardless of backend response
    // Sort predictions client-side to ensure visual consistency
    // This runs efficiently on the small dataset (limit=10) and guarantees correct order
    // regardless of backend response
    const sortedPredictions = useMemo(() => {
      // Create a shallow copy to avoid mutating props
      const sorted = [...filteredPredictions];

      return sorted.sort((a, b) => {
        switch (sortBy) {
          case "confidence":
            // Descending: Higher confidence first
            return b.prediction.confidence - a.prediction.confidence;

          case "date":
            // Ascending: Closest date first
            return (
              new Date(a.match.match_date).getTime() -
              new Date(b.match.match_date).getTime()
            );

          case "home_probability":
            // Descending: Higher probability first
            return (
              b.prediction.home_win_probability -
              a.prediction.home_win_probability
            );

          case "away_probability":
            // Descending: Higher probability first
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
          <Grid container spacing={3}>
            {[...Array(6)].map((_, index) => (
              <Grid item xs={12} sm={6} lg={4} key={index}>
                <MatchCardSkeleton />
              </Grid>
            ))}
          </Grid>
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

    // Empty state
    if (predictions.length === 0) {
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
        {/* Header */}
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
                {predictionCountText}
              </Typography>
            </Box>
          )}

          <Box display="flex" gap={2} flexWrap="wrap" alignItems="center">
            {/* Search removed - hosted in App */}

            {/* Live Toggle */}
            <ToggleButton
              value="check"
              selected={showLiveOnly}
              onChange={handleLiveToggle}
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

        {/* Grid with Suspense for lazy loaded MatchCard */}
        {showLiveOnly ? (
          <Suspense
            fallback={
              <Box display="flex" justifyContent="center" p={4}>
                <CircularProgress />
              </Box>
            }
          >
            <LiveMatchesList
              selectedLeagueIds={league ? [league.id] : []}
              selectedLeagueNames={league ? [league.name] : []}
            />
          </Suspense>
        ) : (
          <Grid container spacing={3}>
            {sortedPredictions.map((matchPrediction, index) => (
              <Grid item xs={12} sm={6} lg={4} key={matchPrediction.match.id}>
                <Suspense fallback={<MatchCardSkeleton />}>
                  <MatchCard
                    matchPrediction={matchPrediction}
                    highlight={index === 0}
                    onClick={() => handleMatchClick(matchPrediction)}
                  />
                </Suspense>
              </Grid>
            ))}
          </Grid>
        )}

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

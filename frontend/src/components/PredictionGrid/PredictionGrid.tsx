/**
 * PredictionGrid Component
 *
 * Grid layout for displaying multiple match predictions.
 * Optimized with React.memo and lazy loading.
 */

import React, {
  memo,
  useMemo,
  Suspense,
  lazy,
  useState,
  useCallback,
} from "react";
import {
  Grid,
  Box,
  Typography,
  CircularProgress,
  Alert,
  Button,
  Skeleton,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
} from "@mui/material";
import { Refresh, SportsSoccer, Sort } from "@mui/icons-material";
import type { MatchPrediction, League } from "../../types";

// Lazy load MatchCard for better initial load performance
const MatchCard = lazy(() => import("../MatchCard"));

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
  onRefresh?: () => void;
  onSortChange?: (sortBy: SortOption, sortDesc: boolean) => void;
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
  ({ predictions, league, loading, error, onRefresh, onSortChange }) => {
    const [sortBy, setSortBy] = useState<SortOption>("confidence");

    // Handle sort change
    const handleSortChange = useCallback(
      (event: SelectChangeEvent<SortOption>) => {
        const newSortBy = event.target.value as SortOption;
        setSortBy(newSortBy);
        if (onSortChange) {
          onSortChange(newSortBy, true);
        }
      },
      [onSortChange]
    );

    // Memoize the prediction count text
    const predictionCountText = useMemo(
      () => `${predictions.length} partidos analizados`,
      [predictions.length]
    );

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
        <Alert
          severity="error"
          action={
            onRefresh && (
              <Button color="inherit" size="small" onClick={onRefresh}>
                Reintentar
              </Button>
            )
          }
        >
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

          <Box display="flex" gap={2} alignItems="center">
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

            {onRefresh && (
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={onRefresh}
                size="small"
              >
                Actualizar
              </Button>
            )}
          </Box>
        </Box>

        {/* Grid with Suspense for lazy loaded MatchCard */}
        <Grid container spacing={3}>
          {predictions.map((matchPrediction) => (
            <Grid item xs={12} sm={6} lg={4} key={matchPrediction.match.id}>
              <Suspense fallback={<MatchCardSkeleton />}>
                <MatchCard matchPrediction={matchPrediction} />
              </Suspense>
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  }
);

PredictionGrid.displayName = "PredictionGrid";

export default PredictionGrid;

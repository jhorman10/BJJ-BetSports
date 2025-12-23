import React, { memo, useMemo, useCallback } from "react";
import { Box, Typography, CircularProgress, Alert, Chip } from "@mui/material";
import { SportsSoccer } from "@mui/icons-material";
import type { MatchPrediction, League } from "../../types";
import PredictionGridHeader, { SortOption } from "./PredictionGridHeader";
import PredictionGridList, { MatchCardSkeleton } from "./PredictionGridList";
import MatchDetailsModal from "../MatchDetails/MatchDetailsModal";
import { ParleyPickItem } from "../Parley/ParleySlip";

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
  onToggleMatchSelection?: (
    match: MatchPrediction,
    pick?: ParleyPickItem
  ) => void;
  onMatchClick?: (match: MatchPrediction) => void;
}
// Note: Props are maintained for compatibility but data fetching is now internal via hook if league is selected
// However, the original component received predictions as props.
// Wait, the original code shows PredictionGrid receives 'predictions' as props, meaning the parent (App.tsx) handles fetching?
// Let me check App.tsx to see who calls usePredictions.

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
    onMatchClick,
  }) => {
    const [selectedMatch, setSelectedMatch] =
      React.useState<MatchPrediction | null>(null);
    const [modalOpen, setModalOpen] = React.useState(false);

    // ... (filteredPredictions useMemo)
    const filteredPredictions = useMemo(() => {
      // ... (existing filter code)
      // Note: 'Live Only' now toggles the view to the LiveMatchesList component
      // which fetches its own real-time data.
      // We ensure we don't double filter if the user just wants to see the grid but searched.
      return predictions.filter((p) => {
        const matchesSearch =
          searchQuery === "" ||
          p.match.home_team.name
            .toLowerCase()
            .includes(searchQuery.toLowerCase()) ||
          p.match.away_team.name
            .toLowerCase()
            .includes(searchQuery.toLowerCase());
        return matchesSearch;
      });
    }, [predictions, searchQuery]);

    const handleMatchClick = useCallback(
      (matchPrediction: MatchPrediction) => {
        if (onMatchClick) {
          onMatchClick(matchPrediction);
        } else {
          setSelectedMatch(matchPrediction);
          setModalOpen(true);
        }
      },
      [onMatchClick]
    );

    const handleToggleSelection = useCallback(
      (match: MatchPrediction) => {
        if (!onToggleMatchSelection) return;

        // Calculate Best Pick Logic (Moved from App.tsx)
        const p = match.prediction;
        const probs = [
          // 1X2
          { type: "1", val: p.home_win_probability, label: "Local" },
          { type: "X", val: p.draw_probability, label: "Empate" },
          { type: "2", val: p.away_win_probability, label: "Visitante" },
          // Goals
          { type: "O2.5", val: p.over_25_probability, label: "Más 2.5 Goles" },
          {
            type: "U2.5",
            val: p.under_25_probability,
            label: "Menos 2.5 Goles",
          },
          // Corners
          {
            type: "O9.5Cor",
            val: p.over_95_corners_probability || 0,
            label: "Más 9.5 Corners",
          },
          {
            type: "U9.5Cor",
            val: p.under_95_corners_probability || 0,
            label: "Menos 9.5 Corners",
          },
          // Cards
          {
            type: "O4.5Card",
            val: p.over_45_cards_probability || 0,
            label: "Más 4.5 Tarjetas",
          },
          {
            type: "U4.5Card",
            val: p.under_45_cards_probability || 0,
            label: "Menos 4.5 Tarjetas",
          },
          // Handicap
          {
            type: "AhHome",
            val: p.handicap_home_probability || 0,
            label: `Local (${
              p.handicap_line && p.handicap_line > 0 ? "+" : ""
            }${p.handicap_line || 0})`,
          },
          {
            type: "AhAway",
            val: p.handicap_away_probability || 0,
            label: `Visitante (${
              p.handicap_line
                ? (p.handicap_line * -1 > 0 ? "+" : "") + p.handicap_line * -1
                : 0
            })`,
          },
        ];

        // Sort descending
        probs.sort((a, b) => b.val - a.val);
        const best = probs[0];

        const pickItem: ParleyPickItem = {
          match: match,
          pick: best.type,
          probability: best.val,
          label: best.label,
        };

        onToggleMatchSelection(match, pickItem);
      },
      [onToggleMatchSelection]
    );

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
        <Alert severity="error" sx={{ mb: 3 }}>
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
          syncStatus={
            <Chip
              label="Sincronización Activa"
              size="small"
              color="success"
              variant="outlined"
              sx={{ height: 24, fontSize: "0.7rem" }}
            />
          }
        />

        <PredictionGridList
          predictions={sortedPredictions}
          onMatchClick={handleMatchClick}
          selectedMatchIds={selectedMatchIds}
          onToggleMatchSelection={handleToggleSelection}
        />

        {/* Modal */}
        <React.Suspense fallback={null}>
          <MatchDetailsModal
            open={modalOpen}
            onClose={handleCloseModal}
            matchPrediction={selectedMatch}
          />
        </React.Suspense>
      </Box>
    );
  }
);

PredictionGrid.displayName = "PredictionGrid";

export default PredictionGrid;

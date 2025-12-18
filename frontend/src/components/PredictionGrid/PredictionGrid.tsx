/**
 * PredictionGrid Component
 *
 * Grid layout for displaying multiple match predictions.
 */

import React from "react";
import {
  Grid,
  Box,
  Typography,
  CircularProgress,
  Alert,
  Button,
} from "@mui/material";
import { Refresh, SportsSoccer } from "@mui/icons-material";
import MatchCard from "../MatchCard";
import { MatchPrediction, League } from "../../types";

interface PredictionGridProps {
  predictions: MatchPrediction[];
  league: League | null;
  loading: boolean;
  error: Error | null;
  onRefresh?: () => void;
}

const PredictionGrid: React.FC<PredictionGridProps> = ({
  predictions,
  league,
  loading,
  error,
  onRefresh,
}) => {
  // Loading state
  if (loading) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        alignItems="center"
        justifyContent="center"
        py={8}
        gap={2}
      >
        <CircularProgress size={48} />
        <Typography color="text.secondary">Cargando predicciones...</Typography>
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
        sx={{
          border: "2px dashed rgba(148, 163, 184, 0.2)",
          borderRadius: 2,
        }}
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
      >
        {league && (
          <Box>
            <Typography variant="h5" fontWeight={600}>
              Predicciones: {league.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {predictions.length} partidos analizados
            </Typography>
          </Box>
        )}

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

      {/* Grid */}
      <Grid container spacing={3}>
        {predictions.map((matchPrediction) => (
          <Grid item xs={12} sm={6} lg={4} key={matchPrediction.match.id}>
            <MatchCard matchPrediction={matchPrediction} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default PredictionGrid;

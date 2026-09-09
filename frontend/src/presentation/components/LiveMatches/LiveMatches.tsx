import React from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  CircularProgress,
  Chip,
  LinearProgress,
  Tooltip,
  IconButton,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import { LiveTv, Refresh } from "@mui/icons-material";

import { useLiveMatches } from "../../../hooks/useLiveMatches";
import { LiveMatchPrediction } from "../../../types";

import MatchCardSkeleton from "./MatchCardSkeleton";
import LiveMatchCard from "./LiveMatchCard";

const LiveMatches: React.FC = () => {
  const { matches, loading, error, refresh } = useLiveMatches();
  const refreshing = loading;
  const processingMessage = "Actualizando marcadores...";

  if (loading) {
    return (
      <Box my={4}>
        <Box display="flex" alignItems="center" gap={1} mb={2}>
          <LiveTv color="error" />
          <Typography variant="h6" fontWeight={600}>Partidos en Vivo</Typography>
        </Box>
        <Card
          sx={{
            background: "rgba(99, 102, 241, 0.1)",
            backdropFilter: "blur(10px)",
            border: "1px solid rgba(99, 102, 241, 0.3)",
            borderRadius: 2,
            mb: 3,
          }}
        >
          <CardContent sx={{ py: 2, display: "flex", alignItems: "center", gap: 2 }}>
            <CircularProgress size={24} color="primary" />
            <Typography color="primary.light" fontWeight={500}>{processingMessage}</Typography>
          </CardContent>
        </Card>
        <Grid container spacing={2}>
          {[...Array(3)].map((_, i) => (
            <Grid size={{ xs: 12, md: 6, lg: 4 }} key={`skeleton-${i}`}>
              <MatchCardSkeleton />
            </Grid>
          ))}
        </Grid>
      </Box>
    );
  }

  if (error || matches.length === 0) return null;

  return (
    <Box my={4}>
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={2}>
        <Box display="flex" alignItems="center" gap={1}>
          <LiveTv color="error" />
          <Typography variant="h6" fontWeight={600}>Partidos en Vivo</Typography>
          <Chip
            label={matches.length}
            color="error"
            size="small"
            sx={{ height: 22, fontSize: "0.75rem", fontWeight: 600 }}
          />
        </Box>
        <Box display="flex" alignItems="center" gap={1}>
          <Tooltip title="Actualizar">
            <IconButton
              size="small"
              onClick={refresh}
              disabled={refreshing}
              sx={{ color: "text.secondary" }}
            >
              <Refresh
                sx={{
                  fontSize: 18,
                  animation: refreshing ? "spin 1s linear infinite" : "none",
                }}
              />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {refreshing && (
        <LinearProgress sx={{ mb: 2, borderRadius: 1, height: 2 }} />
      )}

      <Grid container spacing={2}>
        {matches.map((matchData) => (
          <Grid
            size={{ xs: 12, md: 6, lg: 4 }}
            key={
              "id" in matchData
                ? matchData.id
                : (matchData as LiveMatchPrediction).match?.id
            }
          >
            <LiveMatchCard matchData={matchData} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default LiveMatches;

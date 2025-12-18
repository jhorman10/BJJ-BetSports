import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  CircularProgress,
  Stack,
  Chip,
  Grid,
} from "@mui/material";
import { LiveTv } from "@mui/icons-material";
import { Match } from "../../types";
import api from "../../services/api";

const LiveMatches: React.FC = () => {
  const [matches, setMatches] = useState<Match[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchLiveMatches = async () => {
      try {
        setLoading(true);
        const data = await api.getLiveMatches();
        setMatches(data);
      } catch (err) {
        console.error("Failed to fetch live matches:", err);
        setError("Error al cargar partidos en vivo");
      } finally {
        setLoading(false);
      }
    };

    fetchLiveMatches();
    // Optional: Set up polling every minute
    const interval = setInterval(fetchLiveMatches, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <Box display="flex" alignItems="center" gap={2} my={2}>
        <CircularProgress size={20} color="error" />
        <Typography color="text.secondary">
          Cargando partidos en vivo...
        </Typography>
      </Box>
    );
  }

  if (error || matches.length === 0) {
    // Hide section if no live matches or error, or show empty state
    // For now, let's just return null if no matches to avoid clutter,
    // or a subtle message.
    if (error) return null; // Or show error toast
    return null;
  }

  return (
    <Box my={4}>
      <Box display="flex" alignItems="center" gap={1} mb={2}>
        <LiveTv color="error" />
        <Typography variant="h6" fontWeight={600}>
          Partidos en Vivo Ahora
        </Typography>
        <Chip
          label={matches.length}
          color="error"
          size="small"
          sx={{ height: 20, fontSize: "0.7rem" }}
        />
      </Box>

      <Grid container spacing={2}>
        {matches.map((match) => (
          <Grid item xs={12} md={6} lg={4} key={match.id}>
            <Card
              sx={{
                background: "rgba(30, 41, 59, 0.4)",
                backdropFilter: "blur(5px)",
                border: "1px solid rgba(239, 68, 68, 0.2)",
                borderRadius: 2,
              }}
            >
              <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
                <Stack spacing={1}>
                  <Box
                    display="flex"
                    justifyContent="space-between"
                    alignItems="center"
                  >
                    <Typography
                      variant="caption"
                      color="error.main"
                      fontWeight="bold"
                    >
                      {match.status}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {match.league.name}
                    </Typography>
                  </Box>

                  <Box
                    display="flex"
                    justifyContent="space-between"
                    alignItems="center"
                  >
                    <Box display="flex" alignItems="center" gap={1} flex={1}>
                      <Typography fontWeight={500}>
                        {match.home_team.name}
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        px: 1.5,
                        py: 0.5,
                        bgcolor: "rgba(0,0,0,0.3)",
                        borderRadius: 1,
                        minWidth: 50,
                        textAlign: "center",
                      }}
                    >
                      <Typography fontWeight="bold" color="primary.light">
                        {match.home_goals ?? 0} - {match.away_goals ?? 0}
                      </Typography>
                    </Box>
                    <Box
                      display="flex"
                      alignItems="center"
                      justifyContent="flex-end"
                      gap={1}
                      flex={1}
                    >
                      <Typography fontWeight={500}>
                        {match.away_team.name}
                      </Typography>
                    </Box>
                  </Box>
                </Stack>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default LiveMatches;

import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  Grid,
  CircularProgress,
  Alert,
  TextField,
  InputAdornment,
  Chip,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  SelectChangeEvent,
} from "@mui/material";
import { Search, SportsTennis, SortByAlpha } from "@mui/icons-material";
import { api } from "../../../services/api";
import { TennisUpcomingMatch, TennisTournament } from "../../../types";
import TennisMatchCard from "./TennisMatchCard";

interface TennisPredictionGridProps {
  selectedTournament: TennisTournament | null;
}

type SortOption = "confidence" | "rank" | "name";

const TennisPredictionGrid: React.FC<TennisPredictionGridProps> = ({
  selectedTournament,
}) => {
  const [matches, setMatches] = useState<TennisUpcomingMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("confidence");

  useEffect(() => {
    fetchPredictions();
  }, [selectedTournament]);

  const fetchPredictions = async () => {
    setLoading(true);
    setError(null);
    try {
      if (selectedTournament) {
        const response = await api.getTennisPredictionsByTournament(
          selectedTournament.id
        );
        setMatches(response.matches || []);
      } else {
        const response = await api.getTennisUpcoming();
        setMatches(response.matches || []);
      }
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Error al cargar predicciones";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const filteredMatches = matches
    .filter((match) => {
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      return (
        match.player1.name.toLowerCase().includes(query) ||
        match.player2.name.toLowerCase().includes(query) ||
        match.tournament.toLowerCase().includes(query)
      );
    })
    .sort((a, b) => {
      switch (sortBy) {
        case "confidence":
          return b.prediction.confidence - a.prediction.confidence;
        case "rank":
          return (
            (a.player1.rank || 100) - (b.player1.rank || 100)
          );
        case "name":
          return a.player1.name.localeCompare(b.player1.name);
        default:
          return 0;
      }
    });

  const handleSortChange = (event: SelectChangeEvent<SortOption>) => {
    setSortBy(event.target.value as SortOption);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" py={8}>
        <CircularProgress sx={{ color: "#6366f1" }} />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 3 }}>
        {error}
      </Alert>
    );
  }

  if (matches.length === 0) {
    return (
      <Alert severity="info" sx={{ mb: 3 }}>
        No se encontraron partidos para este torneo.
      </Alert>
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
        <Box display="flex" alignItems="center" gap={1}>
          <SportsTennis sx={{ color: "#6366f1" }} />
          <Typography variant="h6" fontWeight={600}>
            {selectedTournament
              ? `${selectedTournament.name} — Predicciones`
              : "Todos los Partidos"}
          </Typography>
          <Chip
            label={`${filteredMatches.length} partidos`}
            size="small"
            sx={{
              bgcolor: "rgba(99,102,241,0.15)",
              color: "#a5b4fc",
              fontWeight: 600,
            }}
          />
        </Box>

        <Box display="flex" gap={2}>
          {/* Search */}
          <TextField
            size="small"
            placeholder="Buscar jugador..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <Search sx={{ color: "rgba(255,255,255,0.4)", fontSize: 18 }} />
                </InputAdornment>
              ),
            }}
            sx={{
              minWidth: 200,
              "& .MuiOutlinedInput-root": {
                color: "white",
                "& fieldset": { borderColor: "rgba(255,255,255,0.15)" },
                "&:hover fieldset": { borderColor: "rgba(255,255,255,0.3)" },
                "&.Mui-focused fieldset": { borderColor: "#6366f1" },
              },
            }}
          />

          {/* Sort */}
          <FormControl size="small" sx={{ minWidth: 140 }}>
            <InputLabel sx={{ color: "rgba(255,255,255,0.6)" }}>
              Ordenar
            </InputLabel>
            <Select
              value={sortBy}
              onChange={handleSortChange}
              label="Ordenar"
              startAdornment={
                <SortByAlpha sx={{ mr: 0.5, fontSize: 16, color: "rgba(255,255,255,0.4)" }} />
              }
              sx={{
                color: "white",
                "& .MuiOutlinedInput-notchedOutline": {
                  borderColor: "rgba(255,255,255,0.15)",
                },
                "&:hover .MuiOutlinedInput-notchedOutline": {
                  borderColor: "rgba(255,255,255,0.3)",
                },
                "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
                  borderColor: "#6366f1",
                },
              }}
            >
              <MenuItem value="confidence">Mayor confianza</MenuItem>
              <MenuItem value="rank">Mejor ranking</MenuItem>
              <MenuItem value="name">Nombre</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Box>

      {/* Matches Grid */}
      <Grid container spacing={2}>
        {filteredMatches.map((match) => (
          <Grid key={match.match_id} size={{ xs: 12, sm: 6, lg: 4 }}>
            <TennisMatchCard match={match} />
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};

export default TennisPredictionGrid;

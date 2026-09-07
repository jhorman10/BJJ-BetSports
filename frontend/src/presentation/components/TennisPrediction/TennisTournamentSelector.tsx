import React, { useState, useEffect } from "react";
import {
  Box,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  SelectChangeEvent,
} from "@mui/material";
import { SportsTennis } from "@mui/icons-material";
import { api } from "../../../services/api";
import { TennisTournament } from "../../../types";

interface TennisTournamentSelectorProps {
  selectedTournament: TennisTournament | null;
  onSelectTournament: (tournament: TennisTournament | null) => void;
}

const SURFACE_COLORS: Record<string, string> = {
  Hard: "#3b82f6",
  Clay: "#f97316",
  Grass: "#22c55e",
  "Hard (Indoor)": "#6366f1",
  Carpet: "#a855f7",
};

const TennisTournamentSelector: React.FC<TennisTournamentSelectorProps> = ({
  selectedTournament,
  onSelectTournament,
}) => {
  const [tournaments, setTournaments] = useState<TennisTournament[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTournaments();
  }, []);

  const fetchTournaments = async () => {
    try {
      const response = await api.getTennisTournaments();
      setTournaments(response.tournaments || []);
    } catch (err) {
      console.error("Failed to fetch tournaments:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (event: SelectChangeEvent<string>) => {
    const value = event.target.value;
    if (value === "") {
      onSelectTournament(null);
    } else {
      const tournament = tournaments.find((t) => t.id === value);
      onSelectTournament(tournament || null);
    }
  };

  return (
    <Box mb={3}>
      <Box display="flex" alignItems="center" gap={1} mb={1}>
        <SportsTennis sx={{ color: "#6366f1" }} />
        <Typography variant="body2" color="text.secondary">
          Selecciona un torneo para ver las predicciones
        </Typography>
      </Box>

      <FormControl fullWidth size="small" sx={{ maxWidth: 400 }}>
        <InputLabel sx={{ color: "rgba(255,255,255,0.6)" }}>
          Torneo
        </InputLabel>
        <Select
          value={selectedTournament?.id || ""}
          onChange={handleChange}
          label="Torneo"
          disabled={loading}
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
          <MenuItem value="">
            <em>Todos los torneos</em>
          </MenuItem>
          {tournaments.map((tournament) => (
            <MenuItem key={tournament.id} value={tournament.id}>
              <Box display="flex" alignItems="center" gap={1}>
                <Box
                  sx={{
                    width: 12,
                    height: 12,
                    borderRadius: "50%",
                    bgcolor: SURFACE_COLORS[tournament.surface] || "#6366f1",
                  }}
                />
                <span>{tournament.name}</span>
                <Chip
                  label={`${tournament.match_count} partidos`}
                  size="small"
                  sx={{
                    ml: "auto",
                    height: 20,
                    fontSize: "0.7rem",
                    bgcolor: "rgba(255,255,255,0.1)",
                    color: "rgba(255,255,255,0.7)",
                  }}
                />
              </Box>
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {selectedTournament && (
        <Box mt={1} display="flex" gap={1} alignItems="center">
          <Chip
            label={selectedTournament.name}
            size="small"
            onDelete={() => onSelectTournament(null)}
            sx={{
              bgcolor: SURFACE_COLORS[selectedTournament.surface] || "#6366f1",
              color: "white",
              fontWeight: 600,
            }}
          />
          <Typography variant="caption" color="text.secondary">
            {selectedTournament.surface} · {selectedTournament.match_count} partidos
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default TennisTournamentSelector;

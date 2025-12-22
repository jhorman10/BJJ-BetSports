import React, { useMemo } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  Alert,
  IconButton,
  Tooltip,
  Grid,
  styled,
} from "@mui/material";
import { SportsSoccer, Refresh } from "@mui/icons-material";
import { LiveMatch } from "../../hooks/useLiveMatches";
import LiveMatchCard from "./LiveMatchCard";

const LeagueTitle = styled(Typography)(({ theme }) => ({
  color: "rgba(255, 255, 255, 0.7)",
  fontWeight: 700,
  fontSize: "0.9rem",
  marginBottom: theme.spacing(2),
  paddingLeft: theme.spacing(1),
  borderLeft: "3px solid #22c55e",
}));

const PulseDot = styled(Box)({
  width: 8,
  height: 8,
  borderRadius: "50%",
  backgroundColor: "#22c55e",
  animation: "pulse 1.5s infinite ease-in-out",
  willChange: "opacity",
  "@keyframes pulse": {
    "0%": { opacity: 1 },
    "50%": { opacity: 0.4 },
    "100%": { opacity: 1 },
  },
});

interface LiveMatchesViewProps {
  matches: LiveMatch[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
  selectedLeagueIds?: string[];
  selectedLeagueNames?: string[];
  onMatchSelect?: (matchId: string) => void;
}

const LiveMatchesView: React.FC<LiveMatchesViewProps> = ({
  matches,
  loading,
  error,
  onRefresh,
  selectedLeagueIds = [],
  selectedLeagueNames = [],
  onMatchSelect,
}) => {
  // Filtrar y Agrupar por Liga
  const groupedMatches = useMemo(() => {
    // 1. Filtrar por ligas seleccionadas (si hay selección)
    let filtered = matches;
    if (selectedLeagueIds.length > 0) {
      // Intento 1: Filtrado estricto por ID
      const idFiltered = matches.filter((m) =>
        selectedLeagueIds.includes(m.league_id)
      );

      if (idFiltered.length > 0) {
        filtered = idFiltered;
      } else if (selectedLeagueNames.length > 0) {
        // Intento 2: Filtrado por Nombre
        filtered = matches.filter((m) =>
          selectedLeagueNames.some(
            (name) =>
              m.league_name.toLowerCase().includes(name.toLowerCase()) ||
              name.toLowerCase().includes(m.league_name.toLowerCase())
          )
        );
      } else {
        filtered = [];
      }
    }

    // 2. Agrupar por nombre de liga
    return filtered.reduce((groups, match) => {
      const league = match.league_name;
      if (!groups[league]) {
        groups[league] = [];
      }
      groups[league].push(match);
      return groups;
    }, {} as Record<string, LiveMatch[]>);
  }, [matches, selectedLeagueIds, selectedLeagueNames]);

  return (
    <Box>
      {/* Header con Botón de Actualizar */}
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="center"
        px={2}
        py={1.5}
        mb={2}
      >
        <Box display="flex" alignItems="center" gap={1}>
          <PulseDot />
          <Typography variant="subtitle1" fontWeight={700} color="white">
            En Vivo
          </Typography>
        </Box>
        <Tooltip title="Actualizar marcadores">
          <Box component="span">
            <IconButton
              onClick={onRefresh}
              size="small"
              disabled={loading}
              sx={{ color: "rgba(255, 255, 255, 0.7)" }}
            >
              <Refresh
                fontSize="small"
                sx={{
                  animation: loading ? "spin 1s linear infinite" : "none",
                  "@keyframes spin": {
                    "0%": { transform: "rotate(0deg)" },
                    "100%": { transform: "rotate(360deg)" },
                  },
                }}
              />
            </IconButton>
          </Box>
        </Tooltip>
      </Box>

      {/* Contenido Condicional */}
      {loading && matches.length === 0 ? (
        <Box display="flex" justifyContent="center" p={4}>
          <CircularProgress size={30} sx={{ color: "#22c55e" }} />
        </Box>
      ) : error ? (
        <Alert severity="error">{error}</Alert>
      ) : Object.keys(groupedMatches).length === 0 ? (
        <Box textAlign="center" p={4} color="rgba(255, 255, 255, 0.5)">
          <SportsSoccer sx={{ fontSize: 40, opacity: 0.3, mb: 1 }} />
          <Typography variant="body2">
            No hay partidos en vivo en las ligas seleccionadas.
          </Typography>
        </Box>
      ) : (
        /* Lista de Partidos */
        Object.entries(groupedMatches).map(([leagueName, leagueMatches]) => (
          <Box key={leagueName}>
            <LeagueTitle>{leagueName.toUpperCase()}</LeagueTitle>
            <Grid
              container
              spacing={3}
              justifyContent="center"
              sx={{ mb: 4, px: { xs: 2, sm: 4, md: 0 } }}
            >
              {leagueMatches.map((match) => (
                <LiveMatchCard
                  key={match.id}
                  match={match}
                  onSelect={onMatchSelect}
                />
              ))}
            </Grid>
          </Box>
        ))
      )}
    </Box>
  );
};

export default LiveMatchesView;

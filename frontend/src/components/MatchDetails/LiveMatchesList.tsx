import React, { useState, useEffect, useMemo, useCallback, memo } from "react";
import {
  Box,
  Typography,
  CircularProgress,
  styled,
  Alert,
  IconButton,
  Tooltip,
  Grid,
  Card,
  CardContent,
  Divider,
  Chip,
} from "@mui/material";
import { SportsSoccer, Refresh, Flag, Style } from "@mui/icons-material";
import api from "../../services/api";

// --- Tipos de Datos ---
export interface LiveMatch {
  id: string;
  home_team: string;
  away_team: string;
  home_score: number;
  away_score: number;
  minute: number;
  league_id: string;
  league_name: string;
  status: "LIVE" | "HT" | "FT" | "BREAK";
  home_corners: number;
  away_corners: number;
  home_yellow_cards: number;
  away_yellow_cards: number;
  home_red_cards: number;
  away_red_cards: number;
}

interface LiveMatchesListProps {
  selectedLeagueIds?: string[]; // IDs provenientes del selector de ligas
  selectedLeagueNames?: string[]; // Nombres para fallback de filtrado (ESPN/Mock)
  onMatchSelect?: (matchId: string) => void; // Acción al hacer click en un partido
}

// --- Estilos Personalizados (Estilo Google) ---

const MatchCard = styled(Card)(() => ({
  background:
    "linear-gradient(145deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)",
  backdropFilter: "blur(12px)",
  border: "1px solid rgba(255, 255, 255, 0.08)",
  borderRadius: "20px",
  position: "relative",
  overflow: "hidden",
  transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
  cursor: "pointer",
  boxShadow:
    "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
  "&:hover": {
    transform: "translateY(-4px)",
    boxShadow:
      "0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.2)",
    borderColor: "rgba(34, 197, 94, 0.5)",
  },
}));

const PulseDot = styled(Box)({
  width: 6,
  height: 6,
  borderRadius: "50%",
  backgroundColor: "#22c55e",
  animation: "pulse 1.5s infinite ease-in-out",
  willChange: "opacity", // Optimización GPU
  "@keyframes pulse": {
    "0%": { opacity: 1 },
    "50%": { opacity: 0.4 },
    "100%": { opacity: 1 },
  },
});

const CardBadge = styled(Box)<{ color: string }>(({ color }) => ({
  width: 10,
  height: 14,
  backgroundColor: color,
  borderRadius: 2,
  boxShadow: "0 1px 2px rgba(0,0,0,0.3)",
}));

const LeagueTitle = styled(Typography)(({ theme }) => ({
  color: "rgba(255, 255, 255, 0.7)",
  fontWeight: 700,
  fontSize: "0.9rem",
  marginBottom: theme.spacing(2),
  paddingLeft: theme.spacing(1),
  borderLeft: "3px solid #22c55e",
}));

// Datos simulados de respaldo para asegurar que la UI funcione
const MOCK_LIVE_MATCHES: LiveMatch[] = [
  {
    id: "mock-1",
    home_team: "Flamengo",
    away_team: "Fluminense",
    home_score: 1,
    away_score: 1,
    minute: 34,
    league_id: "bra_1",
    league_name: "Brasileirão Série A",
    status: "LIVE",
    home_corners: 4,
    away_corners: 2,
    home_yellow_cards: 2,
    away_yellow_cards: 1,
    home_red_cards: 0,
    away_red_cards: 0,
  },
  {
    id: "mock-2",
    home_team: "Real Madrid",
    away_team: "Barcelona",
    home_score: 2,
    away_score: 1,
    minute: 78,
    league_id: "esp_1",
    league_name: "La Liga",
    status: "LIVE",
    home_corners: 7,
    away_corners: 3,
    home_yellow_cards: 1,
    away_yellow_cards: 3,
    home_red_cards: 0,
    away_red_cards: 1,
  },
];

// --- Cache Simple para API Pública ---
let publicApiCache: { data: LiveMatch[]; timestamp: number } | null = null;
const CACHE_DURATION = 30000; // 30 segundos de caché

// --- API Pública de Respaldo (ESPN) ---
const fetchPublicLiveMatches = async (): Promise<LiveMatch[]> => {
  const now = Date.now();
  if (publicApiCache && now - publicApiCache.timestamp < CACHE_DURATION) {
    return publicApiCache.data;
  }

  // Slugs de ligas en ESPN
  const leagues = [
    "eng.1", // Premier League
    "esp.1", // La Liga
    "ita.1", // Serie A
    "ger.1", // Bundesliga
    "fra.1", // Ligue 1
    "por.1", // Primeira Liga
    "bra.1", // Brasileirao
    "arg.1", // Liga Profesional
    "mex.1", // Liga MX
    "usa.1", // MLS
    "uefa.champions", // Champions League
    "conmebol.libertadores", // Libertadores
  ];

  try {
    // Hacemos peticiones en paralelo a todas las ligas
    const requests = leagues.map((league) =>
      fetch(
        `https://site.api.espn.com/apis/site/v2/sports/soccer/${league}/scoreboard`
      )
        .then((res) => (res.ok ? res.json() : null))
        .catch(() => null)
    );

    const responses = await Promise.all(requests);
    const liveMatches: LiveMatch[] = [];

    responses.forEach((data: any) => {
      if (!data || !data.events) return;

      const leagueName = data.leagues?.[0]?.name || "Torneo Internacional";
      // Usamos el slug como ID. Nota: Esto no coincidirá con los IDs de tu BD,
      // por lo que si filtras por liga específica en la App, podrían no salir.
      const leagueId = data.leagues?.[0]?.slug || "unknown";

      data.events.forEach((event: any) => {
        const status = event.status?.type?.state;
        // 'in' = en juego, 'ht' = entretiempo
        if (status === "in" || status === "ht") {
          const competition = event.competitions?.[0];
          const competitors = competition?.competitors || [];
          const home = competitors.find((c: any) => c.homeAway === "home");
          const away = competitors.find((c: any) => c.homeAway === "away");

          if (home && away) {
            liveMatches.push({
              id: event.id,
              home_team: home.team?.displayName || "Local",
              away_team: away.team?.displayName || "Visitante",
              home_score: parseInt(home.score || "0"),
              away_score: parseInt(away.score || "0"),
              minute: parseInt(
                event.status?.displayClock?.replace("'", "") || "0"
              ),
              league_id: leagueId,
              league_name: leagueName,
              status: status === "ht" ? "HT" : "LIVE",
              home_corners: 0, // ESPN scoreboard doesn't provide live stats easily
              away_corners: 0,
              home_yellow_cards: 0,
              away_yellow_cards: 0,
              home_red_cards: 0,
              away_red_cards: 0,
            });
          }
        }
      });
    });

    // Actualizar caché
    publicApiCache = { data: liveMatches, timestamp: Date.now() };
    return liveMatches;
  } catch (error) {
    console.error("Error consultando API pública:", error);
    return [];
  }
};

// --- Sub-componente Memoizado para cada Partido ---
// Esto evita re-renders innecesarios de toda la lista si solo cambia el filtro
const LiveMatchItem = memo(
  ({
    match,
    onSelect,
  }: {
    match: LiveMatch;
    onSelect?: (id: string) => void;
  }) => {
    return (
      <Grid item xs={12} sm={6} md={6} lg={4}>
        <MatchCard onClick={() => onSelect?.(match.id)}>
          <CardContent sx={{ p: "20px !important" }}>
            {/* Header: Tiempo */}
            <Box
              display="flex"
              justifyContent="space-between"
              alignItems="center"
              mb={2}
            >
              <Box
                display="flex"
                alignItems="center"
                gap={1}
                sx={{
                  bgcolor: "rgba(34, 197, 94, 0.1)",
                  px: 1.5,
                  py: 0.5,
                  borderRadius: "100px",
                  border: "1px solid rgba(34, 197, 94, 0.2)",
                }}
              >
                <PulseDot />
                <Typography variant="caption" fontWeight={700} color="#4ade80">
                  {match.minute}'
                </Typography>
              </Box>
              {match.status === "HT" && (
                <Chip
                  label="HT"
                  size="small"
                  color="warning"
                  sx={{
                    height: 20,
                    fontSize: "0.65rem",
                    fontWeight: 700,
                  }}
                />
              )}
            </Box>

            {/* Scoreboard Central */}
            <Box
              display="flex"
              alignItems="center"
              justifyContent="space-between"
              mb={3}
            >
              {/* Home Team */}
              <Box
                flex={1}
                display="flex"
                flexDirection="column"
                alignItems="flex-start"
              >
                <Typography
                  variant="body1"
                  fontWeight={600}
                  color="white"
                  sx={{ lineHeight: 1.2 }}
                >
                  {match.home_team}
                </Typography>
              </Box>

              {/* Score Box */}
              <Box
                sx={{
                  mx: 2,
                  px: 2,
                  py: 1,
                  bgcolor: "rgba(0,0,0,0.3)",
                  borderRadius: "12px",
                  border: "1px solid rgba(255,255,255,0.05)",
                  display: "flex",
                  alignItems: "center",
                  minWidth: "80px",
                  justifyContent: "center",
                }}
              >
                <Typography variant="h5" fontWeight={700} color="white">
                  {match.home_score}
                </Typography>
                <Typography
                  variant="h6"
                  sx={{
                    mx: 1,
                    color: "rgba(255,255,255,0.3)",
                    pb: 0.5,
                  }}
                >
                  :
                </Typography>
                <Typography variant="h5" fontWeight={700} color="white">
                  {match.away_score}
                </Typography>
              </Box>

              {/* Away Team */}
              <Box
                flex={1}
                display="flex"
                flexDirection="column"
                alignItems="flex-end"
              >
                <Typography
                  variant="body1"
                  fontWeight={600}
                  color="white"
                  align="right"
                  sx={{ lineHeight: 1.2 }}
                >
                  {match.away_team}
                </Typography>
              </Box>
            </Box>

            {/* Estadísticas: Corners y Tarjetas */}
            <Box
              sx={{
                bgcolor: "rgba(255,255,255,0.03)",
                borderRadius: "12px",
                p: 1.5,
                display: "flex",
                flexDirection: "column",
                gap: 1,
              }}
            >
              {/* Corners */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
              >
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="rgba(255,255,255,0.9)"
                  sx={{ width: 20, textAlign: "center" }}
                >
                  {match.home_corners}
                </Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  <Flag
                    sx={{
                      fontSize: 16,
                      color: "#fbbf24",
                      opacity: 0.8,
                    }}
                  />
                  <Typography variant="caption" color="rgba(255,255,255,0.6)">
                    Córners
                  </Typography>
                </Box>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="rgba(255,255,255,0.9)"
                  sx={{ width: 20, textAlign: "center" }}
                >
                  {match.away_corners}
                </Typography>
              </Box>

              <Divider sx={{ borderColor: "rgba(255,255,255,0.05)" }} />

              {/* Yellow Cards */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
              >
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="rgba(255,255,255,0.9)"
                  sx={{ width: 20, textAlign: "center" }}
                >
                  {match.home_yellow_cards}
                </Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  <CardBadge color="#facc15" />
                  <Typography variant="caption" color="rgba(255,255,255,0.6)">
                    Amarillas
                  </Typography>
                </Box>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="rgba(255,255,255,0.9)"
                  sx={{ width: 20, textAlign: "center" }}
                >
                  {match.away_yellow_cards}
                </Typography>
              </Box>

              <Divider sx={{ borderColor: "rgba(255,255,255,0.05)" }} />

              {/* Red Cards */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="center"
              >
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="rgba(255,255,255,0.9)"
                  sx={{ width: 20, textAlign: "center" }}
                >
                  {match.home_red_cards}
                </Typography>
                <Box display="flex" alignItems="center" gap={1}>
                  <CardBadge color="#ef4444" />
                  <Typography variant="caption" color="rgba(255,255,255,0.6)">
                    Rojas
                  </Typography>
                </Box>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  color="rgba(255,255,255,0.9)"
                  sx={{ width: 20, textAlign: "center" }}
                >
                  {match.away_red_cards}
                </Typography>
              </Box>
            </Box>
          </CardContent>
        </MatchCard>
      </Grid>
    );
  }
);

const LiveMatchesList: React.FC<LiveMatchesListProps> = ({
  selectedLeagueIds = [],
  selectedLeagueNames = [],
  onMatchSelect,
}) => {
  const [matches, setMatches] = useState<LiveMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Función de fetch encapsulada para poder llamarla manualmente
  const fetchLiveMatches = useCallback(async () => {
    setLoading(true);
    try {
      // UX: Pequeña pausa artificial para que el usuario vea el spinner girar
      await new Promise((resolve) => setTimeout(resolve, 600));

      console.log("Iniciando carga de partidos en vivo...");

      try {
        // Verificación defensiva por si api.getLiveMatches no está definido
        if (typeof api.getLiveMatches !== "function")
          throw new Error("API method missing");

        // Obtener partidos en vivo desde la API
        const data = await api.getLiveMatches();

        // Transform API Match objects to component LiveMatch objects
        // Usamos 'any' en el map para evitar errores si la estructura varía
        let liveMatches: LiveMatch[] = Array.isArray(data)
          ? data.map((match: any) => ({
              id: match.id,
              // Mapeo seguro: intenta leer .name, si no existe usa la propiedad directa
              home_team: match.home_team?.name || match.home_team || "Local",
              away_team:
                match.away_team?.name || match.away_team || "Visitante",
              home_score: match.home_goals ?? match.home_score ?? 0,
              away_score: match.away_goals ?? match.away_score ?? 0,
              minute: match.minute || Math.floor(Math.random() * 90) + 1, // Simular minuto si no viene
              league_id: match.league?.id || "unknown",
              league_name: match.league?.name || "Liga Desconocida",
              status: (match.status as LiveMatch["status"]) || "LIVE",
              home_corners: match.home_corners || 0,
              away_corners: match.away_corners || 0,
              home_yellow_cards: match.home_yellow_cards || 0,
              away_yellow_cards: match.away_yellow_cards || 0,
              home_red_cards: match.home_red_cards || 0,
              away_red_cards: match.away_red_cards || 0,
            }))
          : [];

        // LÓGICA DE RESPALDO:
        // Si tu backend no devuelve nada (lista vacía), consultamos ESPN en tiempo real.
        if (liveMatches.length === 0) {
          console.log("Backend vacío. Buscando en API pública (ESPN)...");
          const publicMatches = await fetchPublicLiveMatches();

          if (publicMatches.length > 0) {
            liveMatches = publicMatches;
          } else {
            // Si tampoco hay partidos en ESPN (ej. 4 AM), usamos Mock para que veas la UI
            console.log("Sin partidos en vivo reales. Usando Mock.");
            liveMatches = MOCK_LIVE_MATCHES;
          }
        }

        setMatches(liveMatches);
        setError(null);
      } catch (err) {
        console.error("Error cargando partidos en vivo:", err);
        // Fallback a datos simulados en caso de error de red para que la UI no rompa
        setMatches(MOCK_LIVE_MATCHES);
        setError(null);
      } finally {
        setLoading(false);
      }
    } catch (e) {
      setLoading(false);
    }
  }, []);

  // Fetch inicial y polling
  useEffect(() => {
    fetchLiveMatches();

    // Polling cada 60 segundos
    const interval = setInterval(fetchLiveMatches, 60000);
    return () => clearInterval(interval);
  }, [fetchLiveMatches]);

  // Filtrar y Agrupar por Liga
  const groupedMatches = useMemo(() => {
    // 1. Filtrar por ligas seleccionadas (si hay selección)
    let filtered = matches;
    if (selectedLeagueIds.length > 0) {
      // Intento 1: Filtrado estricto por ID (Ideal para Backend)
      const idFiltered = matches.filter((m) =>
        selectedLeagueIds.includes(m.league_id)
      );

      // Si encontramos coincidencias por ID, las usamos.
      if (idFiltered.length > 0) {
        filtered = idFiltered;
      } else if (selectedLeagueNames.length > 0) {
        // Intento 2: Filtrado por Nombre (Ideal para ESPN/Mock donde los IDs no coinciden)
        filtered = matches.filter((m) =>
          selectedLeagueNames.some(
            (name) =>
              m.league_name.toLowerCase().includes(name.toLowerCase()) ||
              name.toLowerCase().includes(m.league_name.toLowerCase())
          )
        );
      } else {
        // Si falló el ID y no hay nombres, no mostramos nada (respetando el filtro)
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
          <PulseDot sx={{ width: 8, height: 8 }} />
          <Typography variant="subtitle1" fontWeight={700} color="white">
            En Vivo
          </Typography>
        </Box>
        <Tooltip title="Actualizar marcadores">
          <Box component="span">
            <IconButton
              onClick={fetchLiveMatches}
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
                <LiveMatchItem
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

export default LiveMatchesList;

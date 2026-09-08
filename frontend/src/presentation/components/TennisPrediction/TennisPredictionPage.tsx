import React, { useState } from "react";
import {
  Box,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Collapse,
  IconButton,
  Grid,
  Divider,
} from "@mui/material";
import {
  SportsTennis,
  ExpandMore,
  ExpandLess,
  Person,
  CalendarMonth,
} from "@mui/icons-material";

import { api } from "../../../services/api";
import { TennisMatchRequest, TennisPredictionResponse } from "../../../types";

const SURFACES = ["Hard", "Clay", "Grass", "Carpet"];
const TOURNAMENT_LEVELS = [
  { value: "G", label: "Grand Slam" },
  { value: "A", label: "ATP" },
  { value: "M", label: "Masters" },
  { value: "D", label: "Davis Cup" },
  { value: "F", label: "Finales" },
];

const cardStyle: React.CSSProperties = {
  background: "rgba(30,41,59,0.5)",
  border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: "12px",
};

const inputSx = {
  "& .MuiOutlinedInput-root": {
    color: "white",
    "& fieldset": { borderColor: "rgba(255,255,255,0.15)" },
    "&:hover fieldset": { borderColor: "rgba(255,255,255,0.3)" },
    "&.Mui-focused fieldset": { borderColor: "#6366f1" },
  },
  "& .MuiInputLabel-root": { color: "rgba(255,255,255,0.6)" },
  "& .MuiInputLabel-root.Mui-focused": { color: "#a5b4fc" },
};

const selectSx = {
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
};

const initialRequest: TennisMatchRequest = {
  tournament_name: "",
  surface: "Hard",
  tourney_level: "G",
  round_name: "",
  match_date: new Date().toISOString().split("T")[0],
  best_of: 3,
  p1_name: "",
  p1_rank: undefined,
  p1_rank_points: undefined,
  p1_age: undefined,
  p1_hand: "R",
  p1_height: undefined,
  p2_name: "",
  p2_rank: undefined,
  p2_rank_points: undefined,
  p2_age: undefined,
  p2_hand: "R",
  p2_height: undefined,
};

const TennisPredictionPage: React.FC = () => {
  const [request, setRequest] = useState<TennisMatchRequest>(initialRequest);
  const [showOdds, setShowOdds] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TennisPredictionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const updateField = <K extends keyof TennisMatchRequest>(
    field: K,
    value: TennisMatchRequest[K]
  ) => {
    setRequest((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    if (!request.p1_name.trim() || !request.p2_name.trim()) {
      setError("Los nombres de los jugadores son obligatorios.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await api.predictTennis(request);
      setResult(response);
    } catch (err: unknown) {
      const message =
        err instanceof Error ? err.message : "Error al obtener la predicción.";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const renderPlayerInputs = (
    label: string,
    prefix: "p1" | "p2"
  ) => (
    <Card sx={cardStyle}>
      <CardContent>
        <Box display="flex" alignItems="center" gap={1} mb={2}>
          <Person sx={{ color: prefix === "p1" ? "#6366f1" : "#10b981" }} />
          <Typography variant="h6" fontWeight={600}>
            {label}
          </Typography>
        </Box>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12 }}>
            <TextField
              fullWidth
              label="Nombre"
              value={request[`${prefix}_name`]}
              onChange={(e) =>
                updateField(`${prefix}_name` as keyof TennisMatchRequest, e.target.value)
              }
              required
              size="small"
              sx={inputSx}
            />
          </Grid>
          <Grid size={{ xs: 6 }}>
            <TextField
              fullWidth
              label="Ranking"
              type="number"
              value={request[`${prefix}_rank`] ?? ""}
              onChange={(e) =>
                updateField(
                  `${prefix}_rank` as keyof TennisMatchRequest,
                  e.target.value ? Number(e.target.value) : undefined
                )
              }
              size="small"
              sx={inputSx}
            />
          </Grid>
          <Grid size={{ xs: 6 }}>
            <TextField
              fullWidth
              label="Puntos"
              type="number"
              value={request[`${prefix}_rank_points`] ?? ""}
              onChange={(e) =>
                updateField(
                  `${prefix}_rank_points` as keyof TennisMatchRequest,
                  e.target.value ? Number(e.target.value) : undefined
                )
              }
              size="small"
              sx={inputSx}
            />
          </Grid>
          <Grid size={{ xs: 4 }}>
            <TextField
              fullWidth
              label="Edad"
              type="number"
              inputProps={{ step: 0.1 }}
              value={request[`${prefix}_age`] ?? ""}
              onChange={(e) =>
                updateField(
                  `${prefix}_age` as keyof TennisMatchRequest,
                  e.target.value ? Number(e.target.value) : undefined
                )
              }
              size="small"
              sx={inputSx}
            />
          </Grid>
          <Grid size={{ xs: 4 }}>
            <TextField
              fullWidth
              label="Altura (cm)"
              type="number"
              value={request[`${prefix}_height`] ?? ""}
              onChange={(e) =>
                updateField(
                  `${prefix}_height` as keyof TennisMatchRequest,
                  e.target.value ? Number(e.target.value) : undefined
                )
              }
              size="small"
              sx={inputSx}
            />
          </Grid>
          <Grid size={{ xs: 4 }}>
            <FormControl fullWidth size="small">
              <InputLabel sx={{ color: "rgba(255,255,255,0.6)" }}>
                Mano
              </InputLabel>
              <Select
                value={request[`${prefix}_hand`] as string}
                onChange={(e) =>
                  updateField(
                    `${prefix}_hand` as keyof TennisMatchRequest,
                    e.target.value
                  )
                }
                label="Mano"
                sx={selectSx}
              >
                <MenuItem value="R">Diestro</MenuItem>
                <MenuItem value="L">Zurdo</MenuItem>
              </Select>
            </FormControl>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );

  return (
    <Box>
      {/* Header */}
      <Box mb={4}>
        <Typography
          variant="h3"
          fontWeight={700}
          sx={{
            background: "linear-gradient(90deg, #6366f1 0%, #10b981 100%)",
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            mb: 1,
          }}
        >
          Predicciones de Tenis
        </Typography>
        <Typography variant="body1" color="text.secondary" maxWidth={600}>
          Análisis estadístico de partidos de tenis basado en ranking, historial
          en superficie y estadísticas de jugadores.
        </Typography>
      </Box>

      {/* Error */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Player Cards */}
      <Grid container spacing={3} mb={3}>
        <Grid size={{ xs: 12, md: 6 }}>
          {renderPlayerInputs("Jugador 1", "p1")}
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          {renderPlayerInputs("Jugador 2", "p2")}
        </Grid>
      </Grid>

      {/* Match Context */}
      <Card sx={{ ...cardStyle, mb: 3 }}>
        <CardContent>
          <Box display="flex" alignItems="center" gap={1} mb={2}>
            <CalendarMonth sx={{ color: "#f59e0b" }} />
            <Typography variant="h6" fontWeight={600}>
              Contexto del Partido
            </Typography>
          </Box>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6 }}>
              <TextField
                fullWidth
                label="Torneo"
                value={request.tournament_name}
                onChange={(e) => updateField("tournament_name", e.target.value)}
                size="small"
                sx={inputSx}
              />
            </Grid>
            <Grid size={{ xs: 6, sm: 3 }}>
              <FormControl fullWidth size="small">
                <InputLabel sx={{ color: "rgba(255,255,255,0.6)" }}>
                  Superficie
                </InputLabel>
                <Select
                  value={request.surface}
                  onChange={(e) => updateField("surface", e.target.value)}
                  label="Superficie"
                  sx={selectSx}
                >
                  {SURFACES.map((s) => (
                    <MenuItem key={s} value={s}>
                      {s}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 6, sm: 3 }}>
              <FormControl fullWidth size="small">
                <InputLabel sx={{ color: "rgba(255,255,255,0.6)" }}>
                  Nivel
                </InputLabel>
                <Select
                  value={request.tourney_level}
                  onChange={(e) => updateField("tourney_level", e.target.value)}
                  label="Nivel"
                  sx={selectSx}
                >
                  {TOURNAMENT_LEVELS.map((l) => (
                    <MenuItem key={l.value} value={l.value}>
                      {l.label}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 6, sm: 3 }}>
              <TextField
                fullWidth
                label="Ronda"
                value={request.round_name}
                onChange={(e) => updateField("round_name", e.target.value)}
                size="small"
                sx={inputSx}
              />
            </Grid>
            <Grid size={{ xs: 6, sm: 3 }}>
              <FormControl fullWidth size="small">
                <InputLabel sx={{ color: "rgba(255,255,255,0.6)" }}>
                  Mejor de
                </InputLabel>
                <Select
                  value={request.best_of}
                  onChange={(e) => updateField("best_of", Number(e.target.value))}
                  label="Mejor de"
                  sx={selectSx}
                >
                  <MenuItem value={3}>3 sets</MenuItem>
                  <MenuItem value={5}>5 sets</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid size={{ xs: 6, sm: 3 }}>
              <TextField
                fullWidth
                label="Fecha"
                type="date"
                value={request.match_date}
                onChange={(e) => updateField("match_date", e.target.value)}
                size="small"
                sx={inputSx}
              />
            </Grid>
          </Grid>

          {/* Odds Section */}
          <Box mt={2}>
            <Divider sx={{ borderColor: "rgba(255,255,255,0.08)", mb: 1 }} />
            <IconButton
              onClick={() => setShowOdds(!showOdds)}
              sx={{ color: "rgba(255,255,255,0.6)", fontSize: "0.85rem" }}
            >
              <Typography variant="caption" mr={0.5}>
                Cuotas opcionales
              </Typography>
              {showOdds ? <ExpandLess /> : <ExpandMore />}
            </IconButton>
            <Collapse in={showOdds}>
              <Grid container spacing={2} mt={1}>
                <Grid size={{ xs: 6 }}>
                  <TextField
                    fullWidth
                    label="Cuotas Jugador 1"
                    type="number"
                    inputProps={{ step: 0.01 }}
                    value={request.p1_odds ?? ""}
                    onChange={(e) =>
                      updateField(
                        "p1_odds",
                        e.target.value ? Number(e.target.value) : undefined
                      )
                    }
                    size="small"
                    sx={inputSx}
                  />
                </Grid>
                <Grid size={{ xs: 6 }}>
                  <TextField
                    fullWidth
                    label="Cuotas Jugador 2"
                    type="number"
                    inputProps={{ step: 0.01 }}
                    value={request.p2_odds ?? ""}
                    onChange={(e) =>
                      updateField(
                        "p2_odds",
                        e.target.value ? Number(e.target.value) : undefined
                      )
                    }
                    size="small"
                    sx={inputSx}
                  />
                </Grid>
              </Grid>
            </Collapse>
          </Box>
        </CardContent>
      </Card>

      {/* Submit Button */}
      <Box display="flex" justifyContent="center" mb={4}>
        <Button
          variant="contained"
          size="large"
          onClick={handleSubmit}
          disabled={loading || !request.p1_name.trim() || !request.p2_name.trim()}
          startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SportsTennis />}
          sx={{
            background: "linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)",
            textTransform: "none",
            fontWeight: 600,
            px: 5,
            py: 1.5,
            borderRadius: 2,
            "&:hover": {
              background: "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
            },
          }}
        >
          {loading ? "Calculando..." : "Predecir Partido"}
        </Button>
      </Box>

      {/* Loading */}
      {loading && (
        <Box display="flex" justifyContent="center" py={6}>
          <CircularProgress sx={{ color: "#6366f1" }} />
        </Box>
      )}

      {/* Results */}
      {result && !loading && (
        <Card sx={cardStyle}>
          <CardContent>
            <Typography variant="h5" fontWeight={700} mb={3} textAlign="center">
              Resultado de la Predicción
            </Typography>

            {/* Probability Bars */}
            <Box mb={3}>
              <Box display="flex" justifyContent="space-between" mb={0.5}>
                <Typography variant="body2" fontWeight={600}>
                  {result.p1_name}
                </Typography>
                <Typography variant="body2" fontWeight={600}>
                  {(result.p1_win_prob * 100).toFixed(1)}%
                </Typography>
              </Box>
              <Box
                sx={{
                  height: 12,
                  borderRadius: 6,
                  bgcolor: "rgba(255,255,255,0.08)",
                  overflow: "hidden",
                }}
              >
                <Box
                  sx={{
                    height: "100%",
                    width: `${result.p1_win_prob * 100}%`,
                    background: "linear-gradient(90deg, #6366f1, #818cf8)",
                    borderRadius: 6,
                    transition: "width 0.6s ease",
                  }}
                />
              </Box>
            </Box>

            <Box mb={3}>
              <Box display="flex" justifyContent="space-between" mb={0.5}>
                <Typography variant="body2" fontWeight={600}>
                  {result.p2_name}
                </Typography>
                <Typography variant="body2" fontWeight={600}>
                  {(result.p2_win_prob * 100).toFixed(1)}%
                </Typography>
              </Box>
              <Box
                sx={{
                  height: 12,
                  borderRadius: 6,
                  bgcolor: "rgba(255,255,255,0.08)",
                  overflow: "hidden",
                }}
              >
                <Box
                  sx={{
                    height: "100%",
                    width: `${result.p2_win_prob * 100}%`,
                    background: "linear-gradient(90deg, #10b981, #34d399)",
                    borderRadius: 6,
                    transition: "width 0.6s ease",
                  }}
                />
              </Box>
            </Box>

            <Divider sx={{ borderColor: "rgba(255,255,255,0.08)", mb: 3 }} />

            {/* Winner & Confidence */}
            <Box textAlign="center">
              <Typography variant="body1" color="text.secondary" mb={1}>
                Ganador predicho
              </Typography>
              <Typography
                variant="h4"
                fontWeight={700}
                sx={{
                  background:
                    "linear-gradient(90deg, #6366f1 0%, #10b981 100%)",
                  backgroundClip: "text",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  mb: 1,
                }}
              >
                {result.predicted_winner === "Player 1"
                  ? result.p1_name
                  : result.p2_name}
              </Typography>
              <Typography variant="h6" color="text.secondary">
                Confianza: {(result.confidence * 100).toFixed(2)}%
              </Typography>
            </Box>

            {/* Metadata */}
            <Box
              mt={3}
              display="flex"
              justifyContent="center"
              gap={3}
              flexWrap="wrap"
            >
              <Typography variant="body2" color="text.secondary">
                <strong>Superficie:</strong> {result.surface}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                <strong>Torneo:</strong> {result.tournament_name}
              </Typography>
            </Box>
          </CardContent>
        </Card>
      )}
    </Box>
  );
};

export default TennisPredictionPage;

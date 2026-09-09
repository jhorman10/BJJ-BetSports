import React, { useState } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Grid,
  Paper,
  Typography,
  Alert,
} from "@mui/material";
import {
  SportsSoccer,
  SportsTennis,
  SportsBaseball,
  SportsBasketball,
  AutoAwesome,
  WarningAmber,
} from "@mui/icons-material";
import type { SvgIconComponent } from "@mui/icons-material";

import api from "../../../services/api";
import { BestCombinationResponse } from "../../../types";

const SPORT_ICONS: Record<string, SvgIconComponent> = {
  soccer: SportsSoccer,
  tennis: SportsTennis,
  baseball: SportsBaseball,
  basketball: SportsBasketball,
};

const SPORT_LABELS: Record<string, string> = {
  soccer: "Fútbol",
  tennis: "Tenis",
  baseball: "Béisbol",
  basketball: "Baloncesto",
};

const RISK_LABELS: Record<number, string> = {
  1: "Riesgo bajo",
  2: "Riesgo moderado",
  3: "Riesgo medio-alto",
  4: "Riesgo alto",
  5: "Riesgo muy alto",
};

function formatProbability(p: number): string {
  return `${(p * 100).toFixed(1)}%`;
}

const FALLBACK_ERROR =
  "No se pudo calcular la mejor combinación. Inténtalo de nuevo.";

function detailFromObject(detail: Record<string, unknown>): string {
  // Backend 409 shape: { error, detail, missing_sports }
  if (typeof detail.detail === "string") return detail.detail;
  if (typeof detail.error === "string") return detail.error;
  if (Array.isArray(detail.missing_sports) && detail.missing_sports.length > 0) {
    return `Deportes sin suficientes picks: ${detail.missing_sports.join(", ")}.`;
  }
  return FALLBACK_ERROR;
}

function extractErrorDetail(err: unknown): string {
  if (typeof err === "object" && err !== null) {
    const axiosErr = err as { response?: { data?: { detail?: unknown } } };
    const detail = axiosErr.response?.data?.detail;
    // 409s serialize detail as an object; Pydantic 422s as an array.
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((entry) => {
          if (typeof entry === "string") return entry;
          if (
            typeof entry === "object" &&
            entry !== null &&
            "msg" in entry &&
            typeof (entry as { msg?: unknown }).msg === "string"
          ) {
            return (entry as { msg: string }).msg;
          }
          return null;
        })
        .filter((msg): msg is string => msg !== null);
      if (messages.length > 0) return messages.join(" ");
    }
    if (typeof detail === "object" && detail !== null) {
      return detailFromObject(detail as Record<string, unknown>);
    }
  }
  return FALLBACK_ERROR;
}

const BestCombinationPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<BestCombinationResponse | null>(null);

  const askModel = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getBestCombination();
      setData(response);
    } catch (err) {
      setError(extractErrorDetail(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      {/* Header */}
      <Box mb={4}>
        <Typography
          variant="h3"
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
          Mejor Combinación
        </Typography>
        <Typography variant="body1" color="text.secondary" maxWidth={640}>
          El modelo selecciona la mejor jugada de alta confianza por deporte
          (fútbol, tenis, béisbol y baloncesto) y arma una combinada de cuatro
          piernas con probabilidad, cuota Esperada y sugerencia de apuesta.
        </Typography>
      </Box>

      {/* CTA */}
      <Box mb={4}>
        <Button
          variant="contained"
          size="large"
          startIcon={<AutoAwesome />}
          onClick={askModel}
          disabled={loading}
          sx={{ textTransform: "none", fontWeight: 700 }}
        >
          {loading ? "Calculando..." : "Pregúntale al modelo"}
        </Button>
      </Box>

      {loading && (
        <Box display="flex" alignItems="center" gap={2} mb={3}>
          <CircularProgress size={24} />
          <Typography color="text.secondary">
            Consultando los modelos de los cuatro deportes...
          </Typography>
        </Box>
      )}

      {error && (
        <Alert
          severity="error"
          sx={{ mb: 3 }}
          action={
            <Button color="inherit" size="small" onClick={askModel}>
              Reintentar
            </Button>
          }
        >
          {error}
        </Alert>
      )}

      {data && data.legs.length === 0 && (
        <Alert severity="info" sx={{ mb: 3 }}>
          No hay jugadas disponibles en este momento. Inténtalo más tarde.
        </Alert>
      )}

      {data && data.legs.length > 0 && (
        <Box>
          {/* Legs */}
          <Grid container spacing={2} mb={3}>
            {data.legs.map((leg) => {
              const Icon = SPORT_ICONS[leg.sport] ?? SportsSoccer;
              return (
                <Grid size={{ xs: 12, sm: 6, md: 3 }} key={`${leg.sport}-${leg.match_id}`}>
                  <Card sx={{ bgcolor: "background.paper", borderRadius: 3, height: "100%" }}>
                    <CardContent>
                      <Box display="flex" alignItems="center" mb={1}>
                        <Icon sx={{ color: "primary.main", mr: 1 }} />
                        <Typography fontWeight={700}>
                          {SPORT_LABELS[leg.sport] ?? leg.sport}
                        </Typography>
                      </Box>
                      <Typography variant="body2" color="text.secondary" mb={0.5}>
                        {leg.match_label}
                      </Typography>
                      <Typography variant="h6" fontWeight={700} mb={1.5}>
                        {leg.pick_label}
                      </Typography>
                      <Box display="flex" gap={1} flexWrap="wrap" mb={1}>
                        {leg.league && (
                          <Chip size="small" label={leg.league} variant="outlined" />
                        )}
                        <Chip
                          size="small"
                          label={
                            leg.odds_source === "market"
                              ? `Cuota de mercado ${leg.odds.toFixed(2)}`
                              : `Cuota justa ${leg.odds.toFixed(2)}`
                          }
                          variant="outlined"
                        />
                      </Box>
                      <Typography variant="body2">
                        Probabilidad:{" "}
                        <strong>{formatProbability(leg.probability)}</strong>
                      </Typography>
                      <Box mt={1} display="flex" gap={1} flexWrap="wrap">
                        {leg.confidence_warning && (
                          <Chip
                            size="small"
                            color="warning"
                            icon={<WarningAmber />}
                            label="Confianza reducida"
                          />
                        )}
                        {leg.odds_warning && (
                          <Chip
                            size="small"
                            color="warning"
                            icon={<WarningAmber />}
                            label="Sin cuota de mercado"
                          />
                        )}
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              );
            })}
          </Grid>

          {/* Aggregate + stake */}
          <Paper sx={{ p: 3, bgcolor: "background.paper", borderRadius: 3, mb: 3 }}>
            <Grid container spacing={3}>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Typography variant="body2" color="text.secondary">
                  Probabilidad total
                </Typography>
                <Typography variant="h5" fontWeight={700}>
                  {formatProbability(data.aggregate.total_probability)}
                </Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Typography variant="body2" color="text.secondary">
                  Cuota total
                </Typography>
                <Typography variant="h5" fontWeight={700}>
                  {data.aggregate.total_odds.toFixed(2)}
                  {data.aggregate.mixed_odds && (
                    <Typography component="span" variant="caption" color="text.secondary">
                      {" "}
                      (mixta)
                    </Typography>
                  )}
                </Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Typography variant="body2" color="text.secondary">
                  Valor esperado
                </Typography>
                <Typography
                  variant="h5"
                  fontWeight={700}
                  color={data.aggregate.expected_value >= 0 ? "success.main" : "error.main"}
                >
                  {(data.aggregate.expected_value * 100).toFixed(1)}%
                </Typography>
              </Grid>
              <Grid size={{ xs: 12, sm: 6, md: 3 }}>
                <Typography variant="body2" color="text.secondary">
                  Apuesta sugerida
                </Typography>
                <Typography variant="h5" fontWeight={700}>
                  {(data.stake.suggested_stake_pct * 100).toFixed(1)}%
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {RISK_LABELS[data.stake.risk_level] ?? `Riesgo ${data.stake.risk_level}`}
                  {" · "}Kelly {Math.round(data.stake.kelly_fraction * 100)}%
                </Typography>
              </Grid>
            </Grid>
          </Paper>

          {/* Warnings + disclaimer */}
          {data.warnings.length > 0 && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              <ul style={{ margin: 0, paddingLeft: 20 }}>
                {data.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            </Alert>
          )}
          <Typography variant="caption" color="text.disabled">
            {data.independence_disclaimer}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default BestCombinationPage;
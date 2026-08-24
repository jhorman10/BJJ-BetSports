import React, { useMemo } from "react";
import {
  Box,
  Typography,
  Card,
  CardContent,
  IconButton,
  Chip,
  List,
  ListItem,
  Divider,
} from "@mui/material";
import { Add, Diamond, LocalActivity } from "@mui/icons-material";

import { usePredictionStore } from "../../../application/stores/usePredictionStore";
import { useParleyStore } from "../../../application/stores/useParleyStore";
import { getTeamDisplayName } from "../../../utils/teamUtils";
import { SuggestedPick, MatchPrediction } from "../../../domain/entities";

export const ParleySuggestions: React.FC = () => {
  const { predictions } = usePredictionStore();
  const { selectedPicks, addPick } = useParleyStore();

  const suggestions = useMemo(() => {
    const selectedMatchIds = new Set(Object.keys(selectedPicks));
    const availablePicks: Array<{
      match: MatchPrediction;
      pick: SuggestedPick;
    }> = [];

    // Busca predicciones de alta confianza que no esten ya seleccionadas
    predictions.forEach((m) => {
      if (selectedMatchIds.has(m.match.id)) return;
      if (!m.prediction || !m.prediction.suggested_picks) return;

      m.prediction.suggested_picks.forEach((pick) => {
        // Consideramos "seguro" a un pick si su probabilidad > 0.75
        // o si es "ML Confianza Alta"
        if (pick.probability > 0.75 || pick.reasoning?.includes("Confianza Alta")) {
          availablePicks.push({
            match: m,
            pick,
          });
        }
      });
    });

    // Ordenar por prioridad/probabilidad y devolver los top 5
    return availablePicks
      .sort((a, b) => b.pick.probability - a.pick.probability)
      .slice(0, 5);
  }, [predictions, selectedPicks]);

  if (suggestions.length === 0) return null;

  return (
    <Card sx={{ mt: 3, bgcolor: "rgba(16, 185, 129, 0.05)", border: "1px solid rgba(16, 185, 129, 0.2)" }}>
      <CardContent>
        <Box sx={{ display: "flex", alignItems: "center", mb: 2 }}>
          <LocalActivity sx={{ color: "#10b981", mr: 1 }} />
          <Typography variant="h6" color="white" fontWeight="bold">
            Sugerencias de Alta Probabilidad
          </Typography>
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Estos picks tienen una probabilidad matemática excepcionalmente alta. Añádelos a tu parlay para incrementar la cuota global con un riesgo controlado.
        </Typography>

        <List disablePadding>
          {suggestions.map(({ match, pick }, idx) => (
            <React.Fragment key={match.match.id}>
              <ListItem
                sx={{
                  display: "flex",
                  justifyContent: "space-between",
                  px: 0,
                  py: 1.5,
                }}
              >
                <Box sx={{ flex: 1 }}>
                  <Typography variant="body2" color="text.secondary">
                    {getTeamDisplayName(match.match.home_team)} vs {getTeamDisplayName(match.match.away_team)}
                  </Typography>
                  <Box sx={{ display: "flex", alignItems: "center", mt: 0.5, gap: 1 }}>
                    <Typography variant="body1" color="white" fontWeight="bold">
                      {pick.market_label}
                    </Typography>
                    <Chip
                      label={`${(pick.probability * 100).toFixed(0)}%`}
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: "0.65rem",
                        color: "#10b981",
                        borderColor: "rgba(16,185,129,0.3)",
                      }}
                      variant="outlined"
                    />
                    {pick.reasoning?.includes("Confianza Alta") && (
                      <Diamond sx={{ fontSize: "1rem", color: "#fbbf24" }} />
                    )}
                  </Box>
                </Box>

                <IconButton
                  color="primary"
                  onClick={() =>
                    addPick(match.match.id, {
                      match: match,
                      pick: pick.pick_code || pick.market_type,
                      label: pick.market_label,
                      probability: pick.probability,
                    })
                  }
                  sx={{
                    bgcolor: "rgba(99, 102, 241, 0.1)",
                    "&:hover": { bgcolor: "rgba(99, 102, 241, 0.2)" },
                  }}
                >
                  <Add />
                </IconButton>
              </ListItem>
              {idx < suggestions.length - 1 && <Divider sx={{ borderColor: "rgba(255,255,255,0.05)" }} />}
            </React.Fragment>
          ))}
        </List>
      </CardContent>
    </Card>
  );
};

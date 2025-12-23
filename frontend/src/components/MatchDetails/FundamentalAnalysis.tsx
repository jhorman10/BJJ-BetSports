import React, { useState } from "react";
import {
  Box,
  Typography,
  Checkbox,
  FormControlLabel,
  Paper,
  LinearProgress,
  Collapse,
  IconButton,
  Tooltip,
  Chip,
} from "@mui/material";
import {
  FactCheck,
  Warning,
  CheckCircle,
  ExpandMore,
  ExpandLess,
} from "@mui/icons-material";

const CHECKLIST_ITEMS = [
  {
    id: "lineups_confirmed",
    label: "Alineaciones Confirmadas (Oficiales)",
  },
  { id: "key_players", label: "Sin bajas de Goleadores/Portero titular" },
  {
    id: "market_sentiment",
    label: "Movimiento de Cuotas estable (Sin caídas drásticas en contra)",
  },
  { id: "fatigue", label: "Descanso suficiente (>72h desde último partido)" },
];

const FundamentalAnalysis: React.FC = () => {
  const [checkedItems, setCheckedItems] = useState<Record<string, boolean>>({});
  const [expanded, setExpanded] = useState(false);

  // Load from local storage based on some key?
  // For now, it's ephemeral per modal open, or we can persist if we pass match ID.
  // Simplifying to ephemeral for this iteration.

  const handleToggle = (id: string) => {
    setCheckedItems((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const checkedCount = Object.values(checkedItems).filter(Boolean).length;
  const progress = (checkedCount / CHECKLIST_ITEMS.length) * 100;

  const isHighRisk = progress < 50;
  const isValidated = progress === 100;

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        mb: 3,
        borderColor: isHighRisk
          ? "warning.main"
          : isValidated
          ? "success.main"
          : "divider",
        bgcolor: isHighRisk
          ? "rgba(237, 108, 2, 0.05)"
          : isValidated
          ? "rgba(46, 125, 50, 0.05)"
          : "transparent",
      }}
    >
      <Box display="flex" alignItems="center" justifyContent="space-between">
        <Box display="flex" alignItems="center" gap={1}>
          <FactCheck color={isValidated ? "success" : "action"} />
          <Typography variant="subtitle1" fontWeight="bold">
            Análisis Fundamental
          </Typography>
        </Box>
        <Box display="flex" alignItems="center" gap={1}>
          {isHighRisk && (
            <Tooltip title="Riesgo: Factores externos no validados">
              <Chip
                label="Riesgo Fundamental"
                color="warning"
                size="small"
                icon={<Warning />}
              />
            </Tooltip>
          )}
          {isValidated && (
            <Chip
              label="Validado"
              color="success"
              size="small"
              icon={<CheckCircle />}
            />
          )}
          <IconButton size="small" onClick={() => setExpanded(!expanded)}>
            {expanded ? <ExpandLess /> : <ExpandMore />}
          </IconButton>
        </Box>
      </Box>

      <Collapse in={expanded} timeout="auto" unmountOnExit={false}>
        <Box mt={2}>
          <Typography variant="body2" color="text.secondary" paragraph>
            <strong>Elimina los datos ciegos:</strong> Verifica estos factores
            fundamentales que el modelo estadístico puro podría no ver.
          </Typography>

          <Box display="flex" flexDirection="column" gap={1}>
            {CHECKLIST_ITEMS.map((item) => (
              <FormControlLabel
                key={item.id}
                control={
                  <Checkbox
                    checked={!!checkedItems[item.id]}
                    onChange={() => handleToggle(item.id)}
                    color="success"
                    size="small"
                  />
                }
                label={<Typography variant="body2">{item.label}</Typography>}
              />
            ))}
          </Box>

          <Box mt={2} display="flex" alignItems="center" gap={1}>
            <Typography variant="caption" color="text.secondary">
              Confianza Fundamental:
            </Typography>
            <Box flex={1}>
              <LinearProgress
                variant="determinate"
                value={progress}
                color={isValidated ? "success" : "warning"}
              />
            </Box>
          </Box>
        </Box>
      </Collapse>
      {!expanded && (
        <Typography
          variant="caption"
          color="text.secondary"
          display="block"
          mt={1}
        >
          {checkedCount}/{CHECKLIST_ITEMS.length} factores verificados. Haz clic
          para expandir.
        </Typography>
      )}
    </Paper>
  );
};

export default FundamentalAnalysis;

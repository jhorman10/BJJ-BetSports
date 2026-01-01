import React, { useEffect, useState } from "react";
import {
  Box,
  Typography,
  LinearProgress,
  CircularProgress,
  keyframes,
} from "@mui/material";
import { SmartToy, Memory, Psychology, CheckCircle } from "@mui/icons-material";
import { useBotStore } from "../../../application/stores/useBotStore";

// Pulse animation for the logo
const pulse = keyframes`
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.05); opacity: 0.8; }
  100% { transform: scale(1); opacity: 1; }
`;

export const SystemInitializationScreen: React.FC = () => {
  const { trainingStatus, trainingMessage, fetchTrainingData } = useBotStore();
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Auto-trigger training if needed
  useEffect(() => {
    if (trainingStatus === "IDLE") {
      fetchTrainingData({ forceRecalculate: true });
    }
  }, [trainingStatus, fetchTrainingData]);

  // Timer for UX
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const steps = [
    {
      label: "Cargando datos históricos (10 años)",
      icon: <Memory />,
      active: elapsedSeconds > 2,
    },
    {
      label: "Entrenando Modelo Random Forest",
      icon: <Psychology />,
      active: elapsedSeconds > 10,
    },
    {
      label: "Optimizando Pesos de Decisión",
      icon: <SmartToy />,
      active: elapsedSeconds > 20,
    },
    {
      label: "Verificando Rentabilidad",
      icon: <CheckCircle />,
      active: elapsedSeconds > 30,
    },
  ];

  return (
    <Box
      sx={{
        position: "fixed",
        top: 0,
        left: 0,
        width: "100vw",
        height: "100vh",
        bgcolor: "#0f172a",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        p: 4,
      }}
    >
      <Box sx={{ animation: `${pulse} 2s infinite ease-in-out`, mb: 4 }}>
        <SmartToy sx={{ fontSize: 80, color: "#10b981" }} />
      </Box>

      <Typography
        variant="h4"
        fontWeight={700}
        color="white"
        gutterBottom
        align="center"
      >
        Inicializando Sistema BJJ
      </Typography>

      <Typography
        variant="body1"
        color="text.secondary"
        sx={{ mb: 4, maxWidth: 500 }}
        align="center"
      >
        Por favor espere. Estamos entrenando el modelo de IA con los datos más
        recientes para garantizar las mejores predicciones.
      </Typography>

      <Box sx={{ width: "100%", maxWidth: 400, mb: 2 }}>
        <LinearProgress
          variant={
            trainingStatus === "IN_PROGRESS" ? "indeterminate" : "determinate"
          }
          value={100}
          color="secondary"
          sx={{ height: 8, borderRadius: 4 }}
        />
      </Box>

      <Typography
        variant="caption"
        color="rgba(255,255,255,0.5)"
        sx={{ mb: 4 }}
      >
        {trainingMessage || "Procesando millones de puntos de datos..."}
      </Typography>

      <Box sx={{ width: "100%", maxWidth: 400 }}>
        {steps.map((step, idx) => (
          <Box
            key={idx}
            sx={{
              display: "flex",
              alignItems: "center",
              mb: 2,
              opacity: step.active ? 1 : 0.3,
              transition: "opacity 0.5s ease",
            }}
          >
            <Box sx={{ color: step.active ? "#10b981" : "grey.700", mr: 2 }}>
              {step.active &&
              trainingStatus === "IN_PROGRESS" &&
              idx === steps.length - 1 ? (
                <CircularProgress size={20} color="inherit" />
              ) : (
                step.icon
              )}
            </Box>
            <Typography variant="body2" color="white">
              {step.label}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  );
};

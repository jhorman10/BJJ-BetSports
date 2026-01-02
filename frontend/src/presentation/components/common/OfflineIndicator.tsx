import React from "react";
import { Typography, Box } from "@mui/material";
import { useOfflineStore } from "../../../application/stores/useOfflineStore";
import { WifiOff, CloudOff } from "@mui/icons-material";

const OfflineIndicator: React.FC = () => {
  const { isOnline, isBackendAvailable } = useOfflineStore();

  // We want to show if either we have no internet OR backend is down
  const showOffline = !isOnline;
  const showBackendDown = isOnline && !isBackendAvailable;

  if (showOffline) {
    return (
      <Box
        sx={{
          position: "fixed",
          bottom: 24,
          left: "50%",
          transform: "translateX(-50%)",
          bgcolor: "rgba(239, 68, 68, 0.9)",
          backdropFilter: "blur(8px)",
          color: "white",
          px: 3,
          py: 1.5,
          borderRadius: 4,
          zIndex: 9999,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 1.5,
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
          border: "1px solid rgba(255, 255, 255, 0.2)",
          animation: "slideUp 0.4s ease-out forwards",
          "@keyframes slideUp": {
            from: {
              transform: "translateX(-50%) translateY(100%)",
              opacity: 0,
            },
            to: { transform: "translateX(-50%) translateY(0)", opacity: 1 },
          },
        }}
      >
        <WifiOff fontSize="small" />
        <Typography
          variant="body2"
          fontWeight={700}
          sx={{ letterSpacing: 0.5 }}
        >
          MODO OFFLINE: Sin conexión a Internet
        </Typography>
      </Box>
    );
  }

  if (showBackendDown) {
    return (
      <Box
        sx={{
          position: "fixed",
          bottom: 24,
          left: "50%",
          transform: "translateX(-50%)",
          bgcolor: "rgba(245, 158, 11, 0.9)",
          backdropFilter: "blur(8px)",
          color: "white",
          px: 3,
          py: 1.5,
          borderRadius: 4,
          zIndex: 9999,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 1.5,
          boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
          border: "1px solid rgba(255, 255, 255, 0.2)",
          animation: "slideUp 0.4s ease-out forwards",
          "@keyframes slideUp": {
            from: {
              transform: "translateX(-50%) translateY(100%)",
              opacity: 0,
            },
            to: { transform: "translateX(-50%) translateY(0)", opacity: 1 },
          },
        }}
      >
        <CloudOff fontSize="small" />
        <Typography
          variant="body2"
          fontWeight={700}
          sx={{ letterSpacing: 0.5 }}
        >
          CONEXIÓN LIMITADA: Servidor no disponible
        </Typography>
      </Box>
    );
  }

  return null;
};

export default OfflineIndicator;

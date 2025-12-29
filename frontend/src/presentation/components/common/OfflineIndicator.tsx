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
          bottom: 0,
          left: 0,
          right: 0,
          bgcolor: "error.main",
          color: "white",
          p: 1,
          zIndex: 9999,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 1,
        }}
      >
        <WifiOff fontSize="small" />
        <Typography variant="body2" fontWeight="bold">
          Sin conexión a Internet. Usando datos guardados.
        </Typography>
      </Box>
    );
  }

  if (showBackendDown) {
    return (
      <Box
        sx={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          bgcolor: "warning.dark",
          color: "white",
          p: 1,
          zIndex: 9999,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 1,
        }}
      >
        <CloudOff fontSize="small" />
        <Typography variant="body2" fontWeight="bold">
          Servidor no disponible. Mostrando datos cacheados.
        </Typography>
      </Box>
    );
  }

  return null;
};

export default OfflineIndicator;

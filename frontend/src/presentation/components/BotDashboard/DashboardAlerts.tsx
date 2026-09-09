import React from "react";
import { Box, Alert, Typography, Button, LinearProgress } from "@mui/material";
import { SmartToy } from "@mui/icons-material";

interface TrainingAlertsProps {
  trainingStatus: string;
  hasActiveTrainingJob: boolean;
  selectedJob: {
    status: string;
    status_message?: string;
    progress_percent?: number;
    job_id: string;
    phase?: string;
  } | null;
  selectedJobEvents: unknown[];
  trainingMessage: string;
  trainingJobsError: string | null;
}

export const TrainingAlerts: React.FC<TrainingAlertsProps> = ({
  trainingStatus,
  hasActiveTrainingJob,
  selectedJob,
  selectedJobEvents,
  trainingMessage,
  trainingJobsError,
}) => (
  <>
    {(trainingStatus === "IN_PROGRESS" || hasActiveTrainingJob) && (
      <Alert severity="info" sx={{ mb: 3 }}>
        <Typography variant="body2">
          ⏳ {hasActiveTrainingJob
            ? `${selectedJob?.status_message || "Entrenamiento en progreso"} (${selectedJob?.progress_percent ?? 0}%)`
            : trainingMessage || "Cargando datos..."}
        </Typography>
        <LinearProgress sx={{ mt: 1, borderRadius: 2 }} />
      </Alert>
    )}
    {selectedJob && (
      <Alert severity={selectedJob.status === "FAILED" ? "error" : "info"} sx={{ mb: 3 }}>
        <Typography variant="body2" fontWeight={700}>
          Job activo: {selectedJob.job_id}
        </Typography>
        <Typography variant="body2">
          Estado: {selectedJob.status} · Fase: {selectedJob.phase ?? "REQUESTED"} · Eventos: {selectedJobEvents.length}
        </Typography>
        <Typography variant="body2">{selectedJob.status_message}</Typography>
      </Alert>
    )}
    {trainingJobsError && !selectedJob && (
      <Alert severity="warning" sx={{ mb: 3 }}>
        {trainingJobsError}
      </Alert>
    )}
  </>
);

interface EmptyStateProps {
  isTrainingServiceUnavailable: boolean;
  error: string | null;
  capabilities: { available: boolean; reasons: Array<{ code: string; message: string }> } | null;
  loading: boolean;
  trainingJobsLoading: boolean;
  hasActiveTrainingJob: boolean;
  onRunTraining: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  isTrainingServiceUnavailable,
  error,
  capabilities,
  loading,
  trainingJobsLoading,
  hasActiveTrainingJob,
  onRunTraining,
}) => {
  const capabilityReasons = capabilities?.reasons ?? [];
  return (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      minHeight="400px"
      textAlign="center"
      sx={{
        bgcolor: "rgba(30, 41, 59, 0.3)",
        borderRadius: 4,
        p: 4,
        border: "1px dashed rgba(148, 163, 184, 0.3)",
      }}
    >
      <SmartToy sx={{ fontSize: 64, color: "rgba(255, 255, 255, 0.2)", mb: 2 }} />
      {isTrainingServiceUnavailable && (
        <Alert severity="warning" sx={{ mb: 3, width: "100%", maxWidth: 560, textAlign: "left" }}>
          <Typography variant="body2" fontWeight={700} sx={{ mb: 0.5 }}>
            Servicio de entrenamiento no disponible
          </Typography>
          <Typography variant="body2">
            {error ||
              "El backend respondio 503 al iniciar el entrenamiento. Espera unos minutos y vuelve a intentar."}
          </Typography>
        </Alert>
      )}
      {!capabilities?.available && capabilityReasons.length > 0 && (
        <Alert severity="warning" sx={{ mb: 3, width: "100%", maxWidth: 560, textAlign: "left" }}>
          <Typography variant="body2" fontWeight={700} sx={{ mb: 0.5 }}>
            Entrenamiento no disponible
          </Typography>
          {capabilityReasons.map((reason) => (
            <Typography key={reason.code} variant="body2">{reason.message}</Typography>
          ))}
        </Alert>
      )}
      <Typography variant="h6" color="white" gutterBottom>
        No hay datos disponibles
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ maxWidth: 500, mb: 3 }}>
        {isTrainingServiceUnavailable
          ? "El entrenamiento no pudo iniciar porque el servicio temporalmente no esta disponible."
          : "No hay datos de entrenamiento. Haz clic en el botón para iniciar."}
      </Typography>
      <Button
        variant="contained"
        onClick={onRunTraining}
        startIcon={<SmartToy />}
        disabled={loading || trainingJobsLoading || hasActiveTrainingJob}
        sx={{
          background: "linear-gradient(135deg, #fbbf24 0%, #d97706 100%)",
          color: "#fff",
          fontWeight: 700,
          px: 4,
          py: 1.5,
        }}
      >
        {hasActiveTrainingJob
          ? "Entrenamiento en progreso"
          : isTrainingServiceUnavailable
          ? "Reintentar entrenamiento"
          : "Cargar Datos"}
      </Button>
    </Box>
  );
};

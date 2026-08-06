import React from "react";
import { Paper, Stack, Typography } from "@mui/material";
import { useTrainingJobsStore } from "../../../application/stores/useTrainingJobsStore";

const TrainingArtifactsPanel: React.FC = () => {
  const { jobs } = useTrainingJobsStore();

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack spacing={1}>
        <Typography variant="h6">Training Artifacts</Typography>
        <Typography variant="body2" color="text.secondary">
          Placeholder inicial para historial, candidatos y promotion flow.
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Jobs observables en el store base: {jobs.length}
        </Typography>
      </Stack>
    </Paper>
  );
};

export default TrainingArtifactsPanel;
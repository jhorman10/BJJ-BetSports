import React from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { useTrainingJobsStore } from "../../../application/stores/useTrainingJobsStore";

const TrainingControlPanel: React.FC = () => {
  const {
    capabilities,
    jobs,
    selectedJobId,
    error,
    isLoading,
    loadCapabilities,
    createJob,
  } = useTrainingJobsStore();

  const initialFormState = {
    modelKey: "",
    executorTarget: "",
    datasetProfile: "",
    featureProfile: "",
    leagueId: "",
    daysBack: "30",
  };

  const [formState, dispatch] = React.useReducer(
    (state: typeof initialFormState, action: { type: string; field?: keyof typeof initialFormState; value?: string }) => {
      switch (action.type) {
        case "SET_FIELD":
          return { ...state, [action.field!]: action.value };
        case "RESET":
          return initialFormState;
        default:
          return state;
      }
    },
    initialFormState
  );

  const { modelKey, executorTarget, datasetProfile, featureProfile, leagueId, daysBack } = formState;

  React.useEffect(() => {
    if (!capabilities) {
      void loadCapabilities().catch(() => undefined);
    }
  }, [capabilities, loadCapabilities]);

  const selectedModel = React.useMemo(
    () =>
      capabilities?.models.find((model) => model.key === modelKey) ??
      capabilities?.models[0] ??
      null,
    [capabilities, modelKey]
  );

  const availableExecutors = React.useMemo(() => {
    if (!capabilities) {
      return [];
    }

    if (!selectedModel) {
      return capabilities.executors.filter((executor) => executor.available);
    }

    return capabilities.executors.filter(
      (executor) => {
        const supportedExecutorSet = new Set(selectedModel.supported_executor_targets);
        return executor.available &&
          supportedExecutorSet.has(executor.key);
      }
    );
  }, [capabilities, selectedModel]);

  const availableDatasetProfiles = React.useMemo(() => {
    if (!capabilities || !selectedModel) {
      return capabilities?.dataset_profiles ?? [];
    }

    return capabilities.dataset_profiles.filter((profile) => {
      const supportedDatasetSet = new Set(selectedModel.supported_dataset_profiles);
      return supportedDatasetSet.has(profile.key);
    });
  }, [capabilities, selectedModel]);

  const availableFeatureProfiles = React.useMemo(() => {
    if (!capabilities || !selectedModel) {
      return capabilities?.feature_profiles ?? [];
    }

    return capabilities.feature_profiles.filter((profile) => {
      const supportedFeatureSet = new Set(selectedModel.supported_feature_profiles);
      return supportedFeatureSet.has(profile.key);
    });
  }, [capabilities, selectedModel]);

  const availableLeagues = React.useMemo(() => {
    if (!capabilities || !selectedModel) {
      return capabilities?.league_options ?? [];
    }

    return capabilities.league_options.filter((league) => {
      const supportedLeagueSet = new Set(selectedModel.supported_league_ids);
      return supportedLeagueSet.has(league.key);
    });
  }, [capabilities, selectedModel]);

  const availableDaysBack = React.useMemo(() => {
    if (!capabilities || !selectedModel) {
      return capabilities?.days_back_options ?? [];
    }

    return capabilities.days_back_options.filter((windowDays) => {
      const supportedDaysBackSet = new Set(selectedModel.supported_days_back);
      return supportedDaysBackSet.has(windowDays);
    });
  }, [capabilities, selectedModel]);

  React.useEffect(() => {
    if (!capabilities || !selectedModel) {
      return;
    }

    dispatch({ type: "SET_FIELD", field: "modelKey", value: modelKey || selectedModel.key });
    dispatch({
      type: "SET_FIELD",
      field: "executorTarget",
      value: executorTarget || selectedModel.default_executor_target || availableExecutors[0]?.key || "",
    });
    dispatch({
      type: "SET_FIELD",
      field: "datasetProfile",
      value: datasetProfile || availableDatasetProfiles[0]?.key || "",
    });
    dispatch({
      type: "SET_FIELD",
      field: "featureProfile",
      value: featureProfile || availableFeatureProfiles[0]?.key || "",
    });
    dispatch({
      type: "SET_FIELD",
      field: "leagueId",
      value: leagueId || availableLeagues[0]?.key || "",
    });
    dispatch({
      type: "SET_FIELD",
      field: "daysBack",
      value: daysBack || String(availableDaysBack[0] ?? 30),
    });
  }, [
    availableDatasetProfiles,
    availableDaysBack,
    availableExecutors,
    availableFeatureProfiles,
    availableLeagues,
    capabilities,
    selectedModel,
  ]);

  const handleSubmit = async (): Promise<void> => {
    if (!selectedModel || !leagueId || !datasetProfile || !featureProfile) {
      return;
    }

    await createJob({
      recipe_id: `manual-${selectedModel.key}`,
      name: "Manual training",
      model_key: selectedModel.key,
      dataset_profile: datasetProfile,
      league_ids: [leagueId],
      days_back: Number(daysBack),
      feature_profile: featureProfile,
      executor_target:
        executorTarget || selectedModel.default_executor_target || "default",
    });
  };

  const capabilityReasons = capabilities?.reasons ?? [];
  const isUnavailable = capabilities ? !capabilities.available : false;

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack spacing={1.5}>
        <Box>
          <Typography variant="h6">Training Control Panel</Typography>
          <Typography variant="body2" color="text.secondary">
            Lanza entrenamientos manuales usando el catalogo real de modelos,
            ejecutores y alcances publicados por backend.
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
          <Chip
            label={`Modelos: ${capabilities?.models.length ?? 0}`}
            size="small"
          />
          <Chip
            label={`Ejecutores: ${capabilities?.executors.length ?? 0}`}
            size="small"
          />
          <Chip label={`Jobs: ${jobs.length}`} size="small" />
          <Chip
            label={selectedJobId ? `Seleccionado: ${selectedJobId}` : "Sin job"}
            size="small"
          />
        </Stack>
        {isUnavailable
          ? capabilityReasons.map((reason) => (
              <Alert key={reason.code} severity="warning">
                {reason.message}
              </Alert>
            ))
          : null}
        {capabilities ? (
          <Stack spacing={1.5}>
            <TextField
              select
              label="Modelo"
              value={selectedModel?.key ?? modelKey}
              onChange={(event) => dispatch({ type: "SET_FIELD", field: "modelKey", value: event.target.value })}
              size="small"
              SelectProps={{ native: true }}
            >
              <option value="" />
              {capabilities.models.map((model) => (
                <option key={model.key} value={model.key}>
                  {model.label}
                </option>
              ))}
            </TextField>
            <TextField
              select
              label="Ejecutor"
              value={executorTarget}
              onChange={(event) => dispatch({ type: "SET_FIELD", field: "executorTarget", value: event.target.value })}
              size="small"
              SelectProps={{ native: true }}
            >
              <option value="" />
              {availableExecutors.map((executor) => (
                <option key={executor.key} value={executor.key}>
                  {executor.label}
                </option>
              ))}
            </TextField>
            <TextField
              select
              label="Dataset"
              value={datasetProfile}
              onChange={(event) => dispatch({ type: "SET_FIELD", field: "datasetProfile", value: event.target.value })}
              size="small"
              SelectProps={{ native: true }}
            >
              <option value="" />
              {availableDatasetProfiles.map((profile) => (
                <option key={profile.key} value={profile.key}>
                  {profile.label}
                </option>
              ))}
            </TextField>
            <TextField
              select
              label="Feature Profile"
              value={featureProfile}
              onChange={(event) => dispatch({ type: "SET_FIELD", field: "featureProfile", value: event.target.value })}
              size="small"
              SelectProps={{ native: true }}
            >
              <option value="" />
              {availableFeatureProfiles.map((profile) => (
                <option key={profile.key} value={profile.key}>
                  {profile.label}
                </option>
              ))}
            </TextField>
            <TextField
              select
              label="Liga"
              value={leagueId}
              onChange={(event) => dispatch({ type: "SET_FIELD", field: "leagueId", value: event.target.value })}
              size="small"
              SelectProps={{ native: true }}
            >
              <option value="" />
              {availableLeagues.map((league) => (
                <option key={league.key} value={league.key}>
                  {league.label}
                </option>
              ))}
            </TextField>
            <TextField
              select
              label="Ventana"
              value={daysBack}
              onChange={(event) => dispatch({ type: "SET_FIELD", field: "daysBack", value: event.target.value })}
              size="small"
              SelectProps={{ native: true }}
            >
              <option value="" />
              {availableDaysBack.map((windowDays) => (
                <option key={windowDays} value={String(windowDays)}>
                  {windowDays} dias
                </option>
              ))}
            </TextField>
            <Button
              variant="contained"
              onClick={() => void handleSubmit()}
              disabled={
                isLoading ||
                isUnavailable ||
                !selectedModel ||
                !executorTarget ||
                !datasetProfile ||
                !featureProfile ||
                !leagueId
              }
            >
              Crear entrenamiento
            </Button>
          </Stack>
        ) : null}
        {error ? <Alert severity="error">{error}</Alert> : null}
      </Stack>
    </Paper>
  );
};

export default TrainingControlPanel;
import React, { useMemo } from "react";
import { Box, Typography, Alert, CircularProgress, Tabs, Tab, Snackbar, Grid } from "@mui/material";

import { MatchPredictionHistory } from "../../../types";
import { useBotStore } from "../../../application/stores/useBotStore";
import { useTrainingJobsStore } from "../../../application/stores/useTrainingJobsStore";
import { useSmartPolling } from "../../../hooks/useSmartPolling";
import { TrainingArtifactsPanel, TrainingControlPanel } from "../Training";

import MatchHistoryTable from "./MatchHistoryTable";
import { DashboardHeader, SummaryCards } from "./DashboardHeader";
import { TrainingAlerts, EmptyState } from "./DashboardAlerts";
import MarketStatsTable from "./MarketStatsTable";
import { calculateMarketStats, formatDate } from "./dashboardUtils";

const BotDashboard: React.FC = () => {
  const {
    stats,
    loading,
    error,
    trainingStatus,
    trainingMessage,
    isTrainingServiceUnavailable,
    fetchTrainingData,
    reconcile,
  } = useBotStore();
  const {
    jobs,
    capabilities,
    selectedJobId,
    selectedJobEvents,
    isLoading: trainingJobsLoading,
    error: trainingJobsError,
    createJob,
    loadCapabilities,
    loadJobs,
    refreshSelectedJob,
  } = useTrainingJobsStore();

  const selectedJob = useMemo(
    () => jobs.find((job) => job.job_id === selectedJobId) ?? null,
    [jobs, selectedJobId]
  );
  const hasActiveTrainingJob =
    selectedJob?.status === "QUEUED" ||
    selectedJob?.status === "VALIDATING" ||
    selectedJob?.status === "PREPARING_DATA" ||
    selectedJob?.status === "RUNNING";

  React.useEffect(() => {
    void loadCapabilities().catch(() => undefined);
  }, [loadCapabilities]);

  useSmartPolling({
    intervalMs: 30000,
    onPoll: reconcile,
    enabled: !loading,
  });

  useSmartPolling({
    intervalMs: 5000,
    onPoll: async () => {
      await refreshSelectedJob();
      const refreshedJob = useTrainingJobsStore
        .getState()
        .jobs.find((job) => job.job_id === useTrainingJobsStore.getState().selectedJobId);
      if (refreshedJob?.status === "COMPLETED") {
        await fetchTrainingData();
      }
    },
    enabled: hasActiveTrainingJob,
  });

  const [displayStartDate, setDisplayStartDate] = React.useState<string>(() => {
    const now = new Date();
    const year = now.getFullYear();
    const targetYear = now.getMonth() === 0 ? year - 1 : year;
    return `${targetYear}-01-01`;
  });

  const [activeTab, setActiveTab] = React.useState(0);
  const [yearMode, setYearMode] = React.useState<"current" | "previous">(() => {
    return new Date().getMonth() === 0 ? "previous" : "current";
  });

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number): void => {
    setActiveTab(newValue);
  };

  const handleYearToggle = (
    _event: React.MouseEvent<HTMLElement>,
    newMode: "current" | "previous" | null
  ): void => {
    if (newMode !== null) {
      setYearMode(newMode);
      const currentYear = new Date().getFullYear();
      const targetYear = newMode === "current" ? currentYear : currentYear - 1;
      setDisplayStartDate(`${targetYear}-01-01`);
    }
  };

  const filteredData = useMemo(() => {
    if (!stats?.match_history) return null;
    const displayDate = new Date(displayStartDate);
    const filteredHistory = stats.match_history.filter(
      (m: MatchPredictionHistory) => new Date(m.match_date) >= displayDate
    );
    let totalPicks = 0;
    let picksWon = 0;
    let picksLost = 0;
    for (const match of filteredHistory) {
      if (match.picks) {
        for (const pick of match.picks) {
          if (pick.was_correct !== undefined) {
            totalPicks++;
            if (pick.was_correct) picksWon++;
            else picksLost++;
          }
        }
      }
    }
    return {
      match_history: filteredHistory,
      total_picks: totalPicks,
      picks_won: picksWon,
      picks_lost: picksLost,
      accuracy: totalPicks > 0 ? (picksWon / totalPicks) * 100 : 0,
      market_stats: calculateMarketStats(filteredHistory),
    };
  }, [stats, displayStartDate]);

  const [notification, setNotification] = React.useState<{
    open: boolean;
    message: string;
    severity: "success" | "error" | "info";
  }>({ open: false, message: "", severity: "info" });

  const runTraining = React.useCallback(
    async (forceRecalculate = false) => {
      try {
        const now = new Date();
        const start = new Date(displayStartDate);
        const diffTime = Math.max(0, now.getTime() - start.getTime());
        const daysBack = Math.max(1, Math.ceil(diffTime / (1000 * 60 * 60 * 24)));
        if (forceRecalculate) {
          await createJob({
            recipe_id: `dashboard-${displayStartDate}`,
            name: "Manual dashboard training",
            model_key: "baseline-model",
            dataset_profile: "dashboard-manual",
            league_ids: ["E0"],
            days_back: daysBack,
            description: `Manual training requested from dashboard since ${displayStartDate}`,
          });
          setNotification({ open: true, message: "Job de entrenamiento creado. Monitoreando progreso...", severity: "info" });
          return;
        }
        await Promise.all([
          fetchTrainingData({ forceRecalculate, daysBack, startDate: displayStartDate }),
          loadJobs().catch(() => undefined),
        ]);
      } catch (trainingError) {
        setNotification({
          open: true,
          message: trainingError instanceof Error ? trainingError.message : "No se pudo iniciar el entrenamiento.",
          severity: "error",
        });
      }
    },
    [createJob, displayStartDate, fetchTrainingData, loadJobs]
  );

  React.useEffect(() => {
    runTraining();
  }, [runTraining]);

  const handleCloseNotification = (): void => {
    setNotification((prev) => ({ ...prev, open: false }));
  };

  if (loading && !filteredData) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error && !filteredData && !isTrainingServiceUnavailable) {
    return <Alert severity="error" sx={{ m: 2 }}>{error}</Alert>;
  }

  return (
    <Box sx={{ minHeight: "100vh", p: 3 }}>
      <Box maxWidth="1400px" mx="auto">
        <DashboardHeader
          yearMode={yearMode}
          displayStartDate={displayStartDate}
          onYearToggle={handleYearToggle}
          onStartChange={setDisplayStartDate}
        />

        <TrainingAlerts
          trainingStatus={trainingStatus}
          hasActiveTrainingJob={hasActiveTrainingJob}
          selectedJob={selectedJob}
          selectedJobEvents={selectedJobEvents}
          trainingMessage={trainingMessage}
          trainingJobsError={trainingJobsError}
        />

        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid size={{ xs: 12, md: 7 }}>
            <TrainingControlPanel />
          </Grid>
          <Grid size={{ xs: 12, md: 5 }}>
            <TrainingArtifactsPanel />
          </Grid>
        </Grid>

        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          sx={{
            mb: 3,
            "& .MuiTab-root": {
              textTransform: "none",
              fontWeight: 700,
              color: "rgba(255,255,255,0.5)",
              "&.Mui-selected": { color: "#fff", bgcolor: "rgba(59, 130, 246, 0.2)" },
            },
          }}
        >
          <Tab label="Resumen" />
          <Tab label="Historial" />
        </Tabs>

        {filteredData ? (
          <Box>
            {activeTab === 0 && (
              <Box>
                <SummaryCards
                  totalPicks={filteredData.total_picks}
                  picksWon={filteredData.picks_won}
                  picksLost={filteredData.picks_lost}
                  accuracy={filteredData.accuracy}
                />
                <MarketStatsTable stats={filteredData.market_stats} />
              </Box>
            )}
            {activeTab === 1 && (
              <Box>
                <Typography variant="h5" fontWeight={700} color="white" gutterBottom>
                  Historial de Picks
                </Typography>
                <Typography variant="body2" color="text.secondary" mb={3}>
                  {filteredData.match_history.length} partidos desde {formatDate(displayStartDate)}
                </Typography>
                <MatchHistoryTable matches={filteredData.match_history} />
              </Box>
            )}
          </Box>
        ) : (
          <EmptyState
            isTrainingServiceUnavailable={isTrainingServiceUnavailable}
            error={error}
            capabilities={capabilities}
            loading={loading}
            trainingJobsLoading={trainingJobsLoading}
            hasActiveTrainingJob={hasActiveTrainingJob}
            onRunTraining={() => runTraining(true)}
          />
        )}

        <Snackbar
          open={notification.open}
          autoHideDuration={6000}
          onClose={handleCloseNotification}
          anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
        >
          <Alert onClose={handleCloseNotification} severity={notification.severity} variant="filled">
            {notification.message}
          </Alert>
        </Snackbar>
      </Box>
    </Box>
  );
};

export default BotDashboard;

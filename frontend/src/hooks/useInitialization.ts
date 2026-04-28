import { useEffect } from "react";
import { usePredictionStore } from "../application/stores/usePredictionStore";
import { useBotStore } from "../application/stores/useBotStore";
import { useLiveStore } from "../application/stores/useLiveStore";
import { useOfflineStore } from "../application/stores/useOfflineStore";

export const useInitialization = () => {
  const fetchLeagues = usePredictionStore((s) => s.fetchLeagues);
  const checkTrainingStatus = usePredictionStore((s) => s.checkTrainingStatus);
  const { fetchTrainingData } = useBotStore();
  const { startPolling, stopPolling } = useLiveStore();
  const checkConnectivity = useOfflineStore((s) => s.checkConnectivity);

  useEffect(() => {
    void checkConnectivity();
    fetchLeagues();
    fetchTrainingData(); // Check bot/training status on startup
    checkTrainingStatus(); // Check for training updates
    startPolling(30000); // Poll every 30 seconds to match backend cache TTL

    // Poll for training updates
    const trainingInterval = setInterval(checkTrainingStatus, 60000);

    return () => {
      stopPolling();
      clearInterval(trainingInterval);
    };
  }, [
    fetchLeagues,
    fetchTrainingData,
    startPolling,
    stopPolling,
    checkConnectivity,
    checkTrainingStatus,
  ]);
};

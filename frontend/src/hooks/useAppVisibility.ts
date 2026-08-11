import { useEffect } from "react";

import { useOfflineStore } from "../application/stores/useOfflineStore";
import { dataReconciliationService } from "../application/services/DataReconciliationService";
import { usePredictionStore } from "../application/stores/usePredictionStore";

export const useAppVisibility = (): void => {
  const { isOnline, isBackendAvailable } = useOfflineStore();
  const checkTrainingStatus = usePredictionStore((s) => s.checkTrainingStatus);

  // Reconciliation: Use centralized service when connectivity restores
  useEffect(() => {
    if (isOnline && isBackendAvailable) {
      dataReconciliationService.reconcileAll();
    }
  }, [isOnline, isBackendAvailable]);

  // Auto-sync when tab becomes visible (user returns to page)
  useEffect(() => {
    const handleVisibilityChange = (): void => {
      if (!document.hidden && isOnline && isBackendAvailable) {
        // Reconcile all stores when user returns to tab
        dataReconciliationService.reconcileAll();
        checkTrainingStatus();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [isOnline, isBackendAvailable, checkTrainingStatus]);
};

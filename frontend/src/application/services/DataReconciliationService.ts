import { usePredictionStore } from "../stores/usePredictionStore";
import { useBotStore } from "../stores/useBotStore";
import { useOfflineStore } from "../stores/useOfflineStore";

/**
 * DataReconciliationService - Centralized service for data synchronization
 *
 * Handles merging of cached and fresh data when connection is restored.
 * Implements smart merging strategies based on timestamps and data types.
 */
class DataReconciliationService {
  private isReconciling = false;

  /**
   * Reconcile all stores
   * Called when connection is restored
   */
  async reconcileAll(): Promise<void> {
    if (this.isReconciling) {
      return;
    }

    const offlineStore = useOfflineStore.getState();

    // Only reconcile if we're online and backend is available
    if (!offlineStore.isOnline || !offlineStore.isBackendAvailable) {
      return;
    }

    this.isReconciling = true;

    try {
      // Run reconciliations in parallel for efficiency
      await Promise.all([this.reconcilePredictions(), this.reconcileBotData()]);

      offlineStore.updateLastSync();
    } catch (error) {
    } finally {
      this.isReconciling = false;
    }
  }

  /**
   * Reconcile predictions and leagues data
   */
  async reconcilePredictions(): Promise<void> {
    const predictionStore = usePredictionStore.getState();

    try {
      // Refetch leagues (lightweight)
      await predictionStore.fetchLeagues();

      // If a league is selected, refetch its predictions (silently)
      if (predictionStore.selectedLeague) {
        await predictionStore.fetchPredictions(true);
      }
    } catch (error) {
      // Don't throw - allow other reconciliations to continue
    }
  }

  /**
   * Reconcile bot dashboard data
   */
  async reconcileBotData(): Promise<void> {
    const botStore = useBotStore.getState();

    try {
      // Use the store's built-in reconcile method
      await botStore.reconcile();
    } catch (error) {
      // Don't throw - keep using cached data
    }
  }

  /**
   * Check if data needs reconciliation
   * @param lastSyncTimestamp - Last sync timestamp
   * @param thresholdMinutes - Threshold in minutes (default: 5)
   */
  needsReconciliation(
    lastSyncTimestamp: number | null,
    thresholdMinutes: number = 5
  ): boolean {
    if (!lastSyncTimestamp) return true;

    const now = Date.now();
    const threshold = thresholdMinutes * 60 * 1000; // Convert to milliseconds

    return now - lastSyncTimestamp > threshold;
  }

  /**
   * Get reconciliation status
   */
  isReconciliationInProgress(): boolean {
    return this.isReconciling;
  }
}

// Singleton instance
export const dataReconciliationService = new DataReconciliationService();

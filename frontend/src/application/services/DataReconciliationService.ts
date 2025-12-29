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
      console.log("Reconciliation already in progress, skipping...");
      return;
    }

    const offlineStore = useOfflineStore.getState();

    // Only reconcile if we're online and backend is available
    if (!offlineStore.isOnline || !offlineStore.isBackendAvailable) {
      console.log("Not online or backend unavailable, skipping reconciliation");
      return;
    }

    this.isReconciling = true;
    console.log("🔄 Starting data reconciliation...");

    try {
      // Run reconciliations in parallel for efficiency
      await Promise.all([this.reconcilePredictions(), this.reconcileBotData()]);

      console.log("✅ Data reconciliation complete");
      offlineStore.updateLastSync();
    } catch (error) {
      console.error("❌ Reconciliation error:", error);
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
      console.log("🔄 Reconciling predictions...");

      // Refetch leagues (lightweight)
      await predictionStore.fetchLeagues();

      // If a league is selected, refetch its predictions
      if (predictionStore.selectedLeague) {
        await predictionStore.fetchPredictions();
      }

      console.log("✅ Predictions reconciled");
    } catch (error) {
      console.error("Failed to reconcile predictions:", error);
      // Don't throw - allow other reconciliations to continue
    }
  }

  /**
   * Reconcile bot dashboard data
   */
  async reconcileBotData(): Promise<void> {
    const botStore = useBotStore.getState();

    try {
      console.log("🔄 Reconciling bot data...");

      // Use the store's built-in reconcile method
      await botStore.reconcile();

      console.log("✅ Bot data reconciled");
    } catch (error) {
      console.error("Failed to reconcile bot data:", error);
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

/**
 * useLiveMatches Hook
 *
 * Optimized hook for fetching and managing live match data with predictions.
 * Features:
 * - Automatic polling every 30 seconds
 * - Loading states with feedback messages
 * - Memoization for performance
 * - Error handling
 */

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { api } from "../services/api";
import { LiveMatchPrediction } from "../types";

// Processing message shown during data loading
const PROCESSING_MESSAGE =
  "Estamos procesando la información para darte las probabilidades con mayor precisión";

// Polling interval in milliseconds (30 seconds)
const POLLING_INTERVAL = 30000;

interface UseLiveMatchesOptions {
  /** Enable automatic polling. Default: true */
  enablePolling?: boolean;
  /** Polling interval in ms. Default: 30000 */
  pollingInterval?: number;
  /** Filter to target leagues only. Default: true */
  filterTargetLeagues?: boolean;
}

interface UseLiveMatchesReturn {
  /** Live matches with predictions */
  matches: LiveMatchPrediction[];
  /** Is initial loading in progress */
  loading: boolean;
  /** Is background refresh in progress */
  refreshing: boolean;
  /** Error object if request failed */
  error: Error | null;
  /** Processing message for user feedback */
  processingMessage: string;
  /** Last successful update timestamp */
  lastUpdated: Date | null;
  /** Manually trigger a refresh */
  refresh: () => Promise<void>;
}

export function useLiveMatches(
  options: UseLiveMatchesOptions = {}
): UseLiveMatchesReturn {
  const {
    enablePolling = true,
    pollingInterval = POLLING_INTERVAL,
    filterTargetLeagues = true,
  } = options;

  const [matches, setMatches] = useState<LiveMatchPrediction[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // Track if this is the first load
  const isFirstLoad = useRef(true);
  // Track if component is mounted
  const isMounted = useRef(true);

  const fetchMatches = useCallback(
    async (isBackground: boolean = false) => {
      // Set appropriate loading state
      if (isBackground) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);

      try {
        const data = await api.getLiveMatchesWithPredictions(
          filterTargetLeagues
        );

        // Only update state if component is still mounted
        if (isMounted.current) {
          setMatches(data);
          setLastUpdated(new Date());
          isFirstLoad.current = false;
        }
      } catch (err) {
        if (isMounted.current) {
          setError(
            err instanceof Error
              ? err
              : new Error("Error al cargar partidos en vivo")
          );
        }
      } finally {
        if (isMounted.current) {
          setLoading(false);
          setRefreshing(false);
        }
      }
    },
    [filterTargetLeagues]
  );

  // Initial fetch
  useEffect(() => {
    isMounted.current = true;
    fetchMatches(false);

    return () => {
      isMounted.current = false;
    };
  }, [fetchMatches]);

  // Polling effect
  useEffect(() => {
    if (!enablePolling) return;

    const intervalId = setInterval(() => {
      // Only poll if not currently loading
      if (!loading && !refreshing) {
        fetchMatches(true);
      }
    }, pollingInterval);

    return () => clearInterval(intervalId);
  }, [enablePolling, pollingInterval, loading, refreshing, fetchMatches]);

  // Manual refresh function
  const refresh = useCallback(async () => {
    await fetchMatches(true);
  }, [fetchMatches]);

  // Memoize the processing message
  const processingMessage = useMemo(() => {
    if (loading && isFirstLoad.current) {
      return PROCESSING_MESSAGE;
    }
    return "";
  }, [loading]);

  // Memoize the return object
  return useMemo(
    () => ({
      matches,
      loading,
      refreshing,
      error,
      processingMessage,
      lastUpdated,
      refresh,
    }),
    [
      matches,
      loading,
      refreshing,
      error,
      processingMessage,
      lastUpdated,
      refresh,
    ]
  );
}

export default useLiveMatches;

import { useEffect, useRef, useCallback } from "react";

interface UseSmartPollingOptions {
  /** Polling interval in milliseconds */
  intervalMs: number;
  /** Callback to execute on each poll */
  onPoll: () => Promise<void> | void;
  /** Whether polling is enabled */
  enabled?: boolean;
  /** Maximum backoff multiplier on errors */
  maxBackoffMultiplier?: number;
}

/**
 * Smart polling hook with visibility awareness and exponential backoff.
 *
 * Features:
 * - Pauses polling when browser tab is not visible (Page Visibility API)
 * - Uses exponential backoff on errors (up to maxBackoffMultiplier)
 * - Cleans up on unmount
 * - Immediately polls when tab becomes visible after being hidden
 */
export function useSmartPolling({
  intervalMs,
  onPoll,
  enabled = true,
  maxBackoffMultiplier = 4,
}: UseSmartPollingOptions) {
  const intervalRef = useRef<number | null>(null);
  const backoffRef = useRef(1);
  const isVisibleRef = useRef(!document.hidden);
  const lastPollTimeRef = useRef<number>(0);
  const isPollingRef = useRef(false);

  // Keep onPoll in a ref so the interval doesn't restart when the callback changes
  const onPollRef = useRef(onPoll);
  useEffect(() => {
    onPollRef.current = onPoll;
  }, [onPoll]);

  const stopPolling = useCallback(() => {
    if (intervalRef.current) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  const poll = useCallback(async () => {
    if (!isVisibleRef.current || !enabled || isPollingRef.current) return;

    isPollingRef.current = true;
    try {
      await onPollRef.current();
      backoffRef.current = 1;
      lastPollTimeRef.current = Date.now();
    } catch {
      backoffRef.current = Math.min(backoffRef.current * 2, maxBackoffMultiplier);
    } finally {
      isPollingRef.current = false;
    }
  }, [enabled, maxBackoffMultiplier]);

  const startPolling = useCallback(() => {
    if (intervalRef.current) return;

    const effectiveInterval = intervalMs * backoffRef.current;
    intervalRef.current = window.setInterval(() => {
      void poll();
    }, effectiveInterval);
  }, [intervalMs, poll]);

  // Handle visibility change
  useEffect(() => {
    const handleVisibilityChange = () => {
      isVisibleRef.current = !document.hidden;

      if (document.hidden) {
        stopPolling();
      } else {
        const timeSinceLastPoll = Date.now() - lastPollTimeRef.current;

        if (timeSinceLastPoll > intervalMs) {
          void poll();
        }

        if (enabled) {
          startPolling();
        }
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [intervalMs, poll, startPolling, stopPolling, enabled]);

  // Start/stop polling based on enabled state
  useEffect(() => {
    if (enabled && isVisibleRef.current) {
      void poll();
      startPolling();
      return () => {
        stopPolling();
      };
    } else {
      stopPolling();
    }

    return () => {
      stopPolling();
    };
  }, [enabled, poll, startPolling, stopPolling]);

  return {
    /** Force an immediate poll */
    pollNow: poll,
  };
}

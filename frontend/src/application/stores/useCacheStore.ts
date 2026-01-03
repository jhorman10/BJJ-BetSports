import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import localforage from "localforage";
import { SuggestedPick } from "../../types";
import api from "../../services/api";

// Configure localforage to use IndexedDB
localforage.config({
  name: "BJJ-BetSports",
  storeName: "picks_cache",
});

const MAX_CACHE_ENTRIES = 100; // Limit cache entries to prevent unlimited growth

interface CacheState {
  // Data
  picksCache: Record<string, { picks: SuggestedPick[]; timestamp: number }>;

  // Status
  fetching: Record<string, boolean>;

  // Actions
  cachePicks: (matchId: string, picks: SuggestedPick[]) => void;
  getPicks: (matchId: string) => SuggestedPick[] | null;
  prefetchMatch: (matchId: string) => Promise<void>;
  isFetching: (matchId: string) => boolean;
  ingestPredictions: (predictions: any[]) => void;
  cleanStaleCache: (ttlSeconds?: number) => void;
}

export const useCacheStore = create<CacheState>()(
  persist(
    (set, get) => ({
      picksCache: {},
      fetching: {},

      cachePicks: (matchId, picks) => {
        set((state) => {
          const newCache = {
            ...state.picksCache,
            [matchId]: {
              picks,
              timestamp: Date.now(),
            },
          };

          // Basic LRU: If cache exceeds max entries, remove oldest
          const keys = Object.keys(newCache);
          if (keys.length > MAX_CACHE_ENTRIES) {
            const oldestKey = keys.sort(
              (a, b) => newCache[a].timestamp - newCache[b].timestamp
            )[0];
            delete newCache[oldestKey];
          }

          return { picksCache: newCache };
        });
      },

      getPicks: (matchId) => {
        const entry = get().picksCache[matchId];
        return entry ? entry.picks : null;
      },

      isFetching: (matchId) => !!get().fetching[matchId],

      prefetchMatch: async (matchId) => {
        const state = get();
        // If already cached and fresh (< 12 hours), skip
        // Or if already fetching, skip
        const cached = state.picksCache[matchId];
        const isFresh =
          cached && Date.now() - cached.timestamp < 1000 * 60 * 30; // 30 min TTL

        if (isFresh || state.fetching[matchId]) return;

        // Set fetching state
        set((s) => ({ fetching: { ...s.fetching, [matchId]: true } }));

        try {
          // Use the dedicated method from api service
          const data = await api.getSuggestedPicks(matchId);

          const picks = data.suggested_picks || [];

          get().cachePicks(matchId, picks);
        } catch (error) {
          // Silent prefetch failure
        } finally {
          set((s) => ({ fetching: { ...s.fetching, [matchId]: false } }));
        }
      },

      ingestPredictions: (predictions: any[]) => {
        // Batch update cache with embedded picks
        set((state) => {
          const newCache = { ...state.picksCache };
          let hasUpdates = false;

          predictions.forEach((p) => {
            const matchId = p.match.id;
            // Check if prediction has valid picks
            if (
              p.prediction &&
              p.prediction.suggested_picks &&
              p.prediction.suggested_picks.length > 0
            ) {
              newCache[matchId] = {
                picks: p.prediction.suggested_picks,
                timestamp: Date.now(),
              };
              hasUpdates = true;
            }
          });

          // Enforce max entries after batch ingest
          const keys = Object.keys(newCache);
          if (keys.length > MAX_CACHE_ENTRIES) {
            const sortedKeys = keys.sort(
              (a, b) => newCache[a].timestamp - newCache[b].timestamp
            );
            const keysToRemove = sortedKeys.slice(
              0,
              sortedKeys.length - MAX_CACHE_ENTRIES
            );
            keysToRemove.forEach((k) => delete newCache[k]);
          }

          return hasUpdates ? { picksCache: newCache } : {};
        });
      },

      cleanStaleCache: (ttlSeconds = 60 * 60 * 24) => {
        // Default 24h cleanup
        const now = Date.now();
        set((state) => {
          const newCache = { ...state.picksCache };
          let changed = false;
          Object.keys(newCache).forEach((key) => {
            if (now - newCache[key].timestamp > ttlSeconds * 1000) {
              delete newCache[key];
              changed = true;
            }
          });
          return changed ? { picksCache: newCache } : state;
        });
      },
    }),
    {
      name: "bjj-bets-cache-storage-v7",
      // Important: Use localforage for IndexedDB support (much larger quota than localStorage)
      storage: createJSONStorage(() => localforage as any),
      partialize: (state) => ({ picksCache: state.picksCache }),
    }
  )
);

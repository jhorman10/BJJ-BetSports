import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { SuggestedPick } from "../../types";
import api from "../../services/api";

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
  cleanStaleCache: (ttlSeconds?: number) => void;
}

export const useCacheStore = create<CacheState>()(
  persist(
    (set, get) => ({
      picksCache: {},
      fetching: {},

      cachePicks: (matchId, picks) => {
        set((state) => ({
          picksCache: {
            ...state.picksCache,
            [matchId]: {
              picks,
              timestamp: Date.now(),
            },
          },
        }));
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
      name: "bjj-bets-cache-storage-v5", // Version bump to force clear cache
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ picksCache: state.picksCache }), // Only persist data, not fetching status
    }
  )
);

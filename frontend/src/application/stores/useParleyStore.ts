import { create } from "zustand";
import { persist } from "zustand/middleware";
import { MatchPrediction } from "../../domain/entities";

export interface ParleyPickItem {
  match: MatchPrediction;
  pick: string;
  probability: number;
  label: string;
}

interface ParleyState {
  selectedPicks: Record<string, ParleyPickItem>;

  // Actions
  addPick: (matchId: string, pick: ParleyPickItem) => void;
  removePick: (matchId: string) => void;
  clearPicks: () => void;
  togglePick: (match: MatchPrediction, pick?: ParleyPickItem | null) => void;
}

export const useParleyStore = create<ParleyState>()(
  persist(
    (set, get) => ({
      selectedPicks: {},

      addPick: (matchId, pick) =>
        set((state) => {
          if (Object.keys(state.selectedPicks).length >= 10) {
            return state;
          }
          return {
            selectedPicks: {
              ...state.selectedPicks,
              [matchId]: pick,
            },
          };
        }),

      removePick: (matchId) =>
        set((state) => {
          const newPicks = { ...state.selectedPicks };
          delete newPicks[matchId];
          return { selectedPicks: newPicks };
        }),

      clearPicks: () => set({ selectedPicks: {} }),

      togglePick: (match, pick) => {
        const matchId = match.match.id;
        const state = get();
        if (state.selectedPicks[matchId]) {
          state.removePick(matchId);
        } else if (pick) {
          state.addPick(matchId, pick);
        }
      },
    }),
    {
      name: "parley-storage",
    }
  )
);

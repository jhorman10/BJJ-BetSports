import { create } from "zustand";
import { MatchPrediction } from "../../domain/entities";

// Re-defining this here or importing from components/Parley/ParleySlip if we refactor that later.
// For now, let's keep it aligned with previous ParleyPickItem but possibly decouple from component.
export interface ParleyPickItem {
  match: MatchPrediction;
  pick: string;
  probability: number;
  label: string;
}

interface ParleyState {
  selectedPicks: Map<string, ParleyPickItem>;

  // Actions
  addPick: (matchId: string, pick: ParleyPickItem) => void;
  removePick: (matchId: string) => void;
  clearPicks: () => void;
  togglePick: (match: MatchPrediction, pick?: ParleyPickItem | null) => void;
}

// Helper to calculate best pick if not provided (logic moved from utils if needed, or imported)
// We will import getBestPick from utils/predictionUtils in the component or here.
// But stores should be pure state. Logic like "calculating best pick" is domain/application logic available to the view.
// We'll keep the store simple: explicit add/remove.

export const useParleyStore = create<ParleyState>((set) => ({
  selectedPicks: new Map(),

  addPick: (matchId, pick) =>
    set((state) => {
      const newMap = new Map(state.selectedPicks);
      if (newMap.size >= 10) {
        // We can throw error or handle validation in UI.
        // Ideally returns failure or state update with error.
        // For simple migration, we just don't add.
        return state;
      }
      newMap.set(matchId, pick);
      return { selectedPicks: newMap };
    }),

  removePick: (matchId) =>
    set((state) => {
      const newMap = new Map(state.selectedPicks);
      newMap.delete(matchId);
      return { selectedPicks: newMap };
    }),

  clearPicks: () => set({ selectedPicks: new Map() }),

  // This generic toggle is useful but might need logic injection for "best pick default"
  // For now, we assume the caller provides the pick or we might handle it in the component.
  // We'll expose simple primitives primarily.
  togglePick: (match, pick) =>
    set((state) => {
      const matchId = match.match.id;
      const newMap = new Map(state.selectedPicks);
      if (newMap.has(matchId)) {
        newMap.delete(matchId);
      } else if (pick) {
        if (newMap.size >= 10) return state;
        newMap.set(matchId, pick);
      }
      return { selectedPicks: newMap };
    }),
}));

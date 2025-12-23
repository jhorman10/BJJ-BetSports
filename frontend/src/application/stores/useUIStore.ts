import { create } from "zustand";
import { MatchPrediction } from "../../domain/entities";

interface UIState {
  currentView: "predictions" | "bot";
  isParleySlipOpen: boolean;
  liveModalOpen: boolean;
  selectedLiveMatch: MatchPrediction | null;
  goalToast: {
    open: boolean;
    message: string;
  };
  showLive: boolean; // Toggle for showing live matches vs predictions

  // Actions
  setView: (view: "predictions" | "bot") => void;
  toggleParleySlip: () => void;
  setParleySlipOpen: (isOpen: boolean) => void;
  openLiveMatchModal: (match: MatchPrediction) => void;
  closeLiveMatchModal: () => void;
  showGoalToast: (message: string) => void;
  closeGoalToast: () => void;
  toggleShowLive: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  currentView: "predictions",
  isParleySlipOpen: false,
  liveModalOpen: false,
  selectedLiveMatch: null,
  goalToast: { open: false, message: "" },
  showLive: false,

  setView: (view) => set({ currentView: view }),
  toggleParleySlip: () =>
    set((state) => ({ isParleySlipOpen: !state.isParleySlipOpen })),
  setParleySlipOpen: (isOpen) => set({ isParleySlipOpen: isOpen }),
  openLiveMatchModal: (match) =>
    set({ liveModalOpen: true, selectedLiveMatch: match }),
  closeLiveMatchModal: () =>
    set({ liveModalOpen: false, selectedLiveMatch: null }),
  showGoalToast: (message) => set({ goalToast: { open: true, message } }),
  closeGoalToast: () =>
    set((state) => ({ goalToast: { ...state.goalToast, open: false } })),
  toggleShowLive: () => set((state) => ({ showLive: !state.showLive })),
}));

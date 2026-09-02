import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

import { MatchPrediction } from "../../domain/entities";
import { Sport, DEFAULT_SPORT } from "../../config/constants";

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
  selectedSport: Sport; // Current sport filter

  // Actions
  setView: (view: "predictions" | "bot") => void;
  toggleParleySlip: () => void;
  setParleySlipOpen: (isOpen: boolean) => void;
  openLiveMatchModal: (match: MatchPrediction) => void;
  closeLiveMatchModal: () => void;
  showGoalToast: (message: string) => void;
  closeGoalToast: () => void;
  toggleShowLive: () => void;
  setSport: (sport: Sport) => void;
}

const SPORT_STORAGE_KEY = "selected-sport";

function loadInitialSport(): Sport {
  if (typeof window === "undefined") return DEFAULT_SPORT;
  try {
    const saved = window.localStorage.getItem(SPORT_STORAGE_KEY);
    if (saved === "tennis" || saved === "baseball" || saved === "basketball" || saved === "soccer") {
      return saved as Sport;
    }
  } catch {
    // ignore
  }
  return DEFAULT_SPORT;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      currentView: "predictions",
      isParleySlipOpen: false,
      liveModalOpen: false,
      selectedLiveMatch: null,
      goalToast: { open: false, message: "" },
      showLive: false,
      selectedSport: loadInitialSport(),

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
      setSport: (sport) => {
        try {
          window.localStorage.setItem(SPORT_STORAGE_KEY, sport);
        } catch {
          // ignore
        }
        set({ selectedSport: sport });
      },
    }),
    {
      name: "ui-store",
      storage: createJSONStorage(() => sessionStorage),
      partialize: (state) => ({
        currentView: state.currentView,
        showLive: state.showLive,
        selectedSport: state.selectedSport,
      }),
    }
  )
);

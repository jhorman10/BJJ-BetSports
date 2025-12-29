import { create } from "zustand";

interface OfflineState {
  isOnline: boolean;
  isBackendAvailable: boolean;
  lastSync: number | null; // Timestamp
  setOnline: (status: boolean) => void;
  setBackendAvailable: (status: boolean) => void;
  updateLastSync: () => void;
  checkConnectivity: () => Promise<void>;
}

export const useOfflineStore = create<OfflineState>((set, get) => ({
  isOnline: navigator.onLine,
  isBackendAvailable: true,
  lastSync: null,

  setOnline: (status) => set({ isOnline: status }),
  setBackendAvailable: (status) => set({ isBackendAvailable: status }),
  updateLastSync: () => set({ lastSync: Date.now() }),

  checkConnectivity: async () => {
    // 1. Basic network check
    if (!navigator.onLine) {
      set({ isOnline: false });
      return;
    }

    set({ isOnline: true });

    // 2. Check Backend Health (optional, or just rely on API failure)
    // We can assume backend is available until proven otherwise by an API error
    // so we won't ping explicitly constantly, but we can do a quick check on mount if needed.
  },
}));

// Setup global listeners
if (typeof window !== "undefined") {
  window.addEventListener("online", () =>
    useOfflineStore.getState().setOnline(true)
  );
  window.addEventListener("offline", () =>
    useOfflineStore.getState().setOnline(false)
  );
}

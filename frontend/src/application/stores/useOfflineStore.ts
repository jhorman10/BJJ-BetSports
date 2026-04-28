import { create } from "zustand";
import { api } from "../../services/api";

const CONNECTIVITY_CHECK_TIMEOUT_MS = 3000;

const getBrowserOnlineState = (): boolean => {
  if (typeof navigator === "undefined") {
    return true;
  }

  return navigator.onLine;
};

const withTimeout = <T>(promise: Promise<T>, timeoutMs: number): Promise<T> =>
  new Promise<T>((resolve, reject) => {
    const timeoutId = window.setTimeout(() => {
      reject(new Error("Connectivity check timed out"));
    }, timeoutMs);

    promise.then(
      (value) => {
        window.clearTimeout(timeoutId);
        resolve(value);
      },
      (error) => {
        window.clearTimeout(timeoutId);
        reject(error);
      }
    );
  });

interface OfflineState {
  isOnline: boolean;
  isBackendAvailable: boolean;
  lastSync: number | null; // Timestamp
  setOnline: (status: boolean) => void;
  setBackendAvailable: (status: boolean) => void;
  updateLastSync: () => void;
  checkConnectivity: () => Promise<void>;
}

export const useOfflineStore = create<OfflineState>((set) => ({
  isOnline: true,
  isBackendAvailable: true,
  lastSync: null,

  setOnline: (status) => set({ isOnline: status }),
  setBackendAvailable: (status) => set({ isBackendAvailable: status }),
  updateLastSync: () => set({ lastSync: Date.now() }),

  checkConnectivity: async () => {
    const browserOnline = getBrowserOnlineState();

    if (!browserOnline) {
      set({ isOnline: false, isBackendAvailable: false });
      return;
    }

    try {
      await withTimeout(api.healthCheck(), CONNECTIVITY_CHECK_TIMEOUT_MS);
      set({ isOnline: true, isBackendAvailable: true });
    } catch {
      set({
        isOnline: browserOnline,
        isBackendAvailable: false,
      });
    }
  },
}));

// Setup global listeners
if (typeof window !== "undefined") {
  const recheckConnectivity = () => {
    void useOfflineStore.getState().checkConnectivity();
  };

  window.addEventListener("online", recheckConnectivity);
  window.addEventListener("offline", recheckConnectivity);
}

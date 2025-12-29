/**
 * LocalStorageObserver - Observer pattern for efficient localStorage operations
 *
 * Features:
 * - Debounced writes to avoid excessive localStorage operations
 * - Multiple subscribers per key
 * - Automatic cleanup
 * - Error handling and fallback
 */

type StorageCallback = (data: any) => void;

class LocalStorageObserver {
  private subscribers: Map<string, Set<StorageCallback>>;
  private debounceTimers: Map<string, NodeJS.Timeout>;
  private readonly DEFAULT_DEBOUNCE_MS = 500;

  constructor() {
    this.subscribers = new Map();
    this.debounceTimers = new Map();

    // Listen for storage events from other tabs
    if (typeof window !== "undefined") {
      window.addEventListener("storage", this.handleStorageEvent);
    }
  }

  /**
   * Subscribe to changes for a specific key
   * @param key - localStorage key to watch
   * @param callback - Function to call when data changes
   * @returns Unsubscribe function
   */
  subscribe(key: string, callback: StorageCallback): () => void {
    if (!this.subscribers.has(key)) {
      this.subscribers.set(key, new Set());
    }

    this.subscribers.get(key)!.add(callback);

    // Return unsubscribe function
    return () => {
      const callbacks = this.subscribers.get(key);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          this.subscribers.delete(key);
          // Clear any pending debounce timer
          const timer = this.debounceTimers.get(key);
          if (timer) {
            clearTimeout(timer);
            this.debounceTimers.delete(key);
          }
        }
      }
    };
  }

  /**
   * Notify all subscribers for a key
   * @param key - localStorage key
   * @param data - Data to pass to callbacks
   */
  notify(key: string, data: any): void {
    const callbacks = this.subscribers.get(key);
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback(data);
        } catch (error) {
          console.error(
            `Error in localStorage observer callback for key ${key}:`,
            error
          );
        }
      });
    }
  }

  /**
   * Persist data to localStorage with optional debouncing
   * @param key - localStorage key
   * @param data - Data to persist
   * @param debounceMs - Debounce delay in milliseconds (default: 500ms)
   */
  persist(
    key: string,
    data: any,
    debounceMs: number = this.DEFAULT_DEBOUNCE_MS
  ): void {
    // Clear existing timer
    const existingTimer = this.debounceTimers.get(key);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }

    // Set new debounced timer
    const timer = setTimeout(() => {
      try {
        const serialized = JSON.stringify(data);
        localStorage.setItem(key, serialized);
        this.notify(key, data);
        this.debounceTimers.delete(key);
      } catch (error) {
        console.error(`Failed to persist data for key ${key}:`, error);

        // Check if quota exceeded
        if (
          error instanceof DOMException &&
          error.name === "QuotaExceededError"
        ) {
          console.warn("localStorage quota exceeded. Attempting cleanup...");
          this.cleanup();

          // Retry once after cleanup
          try {
            const serialized = JSON.stringify(data);
            localStorage.setItem(key, serialized);
            this.notify(key, data);
          } catch (retryError) {
            console.error("Failed to persist even after cleanup:", retryError);
          }
        }
      }
    }, debounceMs);

    this.debounceTimers.set(key, timer);
  }

  /**
   * Get data from localStorage
   * @param key - localStorage key
   * @returns Parsed data or null if not found/invalid
   */
  get<T = any>(key: string): T | null {
    try {
      const item = localStorage.getItem(key);
      if (!item) return null;
      return JSON.parse(item) as T;
    } catch (error) {
      console.error(`Failed to get data for key ${key}:`, error);
      return null;
    }
  }

  /**
   * Remove data from localStorage
   * @param key - localStorage key
   */
  remove(key: string): void {
    try {
      localStorage.removeItem(key);
      this.notify(key, null);
    } catch (error) {
      console.error(`Failed to remove key ${key}:`, error);
    }
  }

  /**
   * Handle storage events from other tabs
   */
  private handleStorageEvent = (event: StorageEvent): void => {
    if (event.key && event.newValue) {
      try {
        const data = JSON.parse(event.newValue);
        this.notify(event.key, data);
      } catch (error) {
        console.error("Failed to parse storage event data:", error);
      }
    }
  };

  /**
   * Cleanup old data to free up space
   * Removes items older than 30 days
   */
  private cleanup(): void {
    const THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000;
    const now = Date.now();

    const keysToRemove: string[] = [];

    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (!key) continue;

      try {
        const item = localStorage.getItem(key);
        if (!item) continue;

        const parsed = JSON.parse(item);

        // Check if item has a timestamp and is old
        if (parsed.timestamp) {
          const timestamp = new Date(parsed.timestamp).getTime();
          if (now - timestamp > THIRTY_DAYS_MS) {
            keysToRemove.push(key);
          }
        }
      } catch {
        // Skip items that can't be parsed
        continue;
      }
    }

    // Remove old items
    keysToRemove.forEach((key) => {
      try {
        localStorage.removeItem(key);
        console.log(`Removed old localStorage item: ${key}`);
      } catch (error) {
        console.error(`Failed to remove old item ${key}:`, error);
      }
    });
  }

  /**
   * Get total localStorage size in bytes
   */
  getStorageSize(): number {
    let total = 0;
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key) {
        const item = localStorage.getItem(key);
        if (item) {
          total += key.length + item.length;
        }
      }
    }
    return total;
  }

  /**
   * Cleanup on destroy
   */
  destroy(): void {
    // Clear all timers
    this.debounceTimers.forEach((timer) => clearTimeout(timer));
    this.debounceTimers.clear();

    // Clear subscribers
    this.subscribers.clear();

    // Remove event listener
    if (typeof window !== "undefined") {
      window.removeEventListener("storage", this.handleStorageEvent);
    }
  }
}

// Singleton instance
export const localStorageObserver = new LocalStorageObserver();

// Export class for testing
export { LocalStorageObserver };

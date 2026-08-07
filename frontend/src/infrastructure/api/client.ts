import axios, { AxiosInstance } from "axios";
import { APP_CONFIG } from "../../config/constants";

// API base URL from environment or default
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Create configured Axios instance
 */
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: APP_CONFIG.API_DEFAULT_TIMEOUT,
    headers: {
      "Content-Type": "application/json",
    },
  });

  // Request interceptor: inject X-API-Key for admin training endpoints when
  // VITE_ADMIN_API_KEY is set at build time. Read at request time so keyless
  // builds and the local dev bypass stay unchanged. Never log the key.
  client.interceptors.request.use((config) => {
    const apiKey = import.meta.env.VITE_ADMIN_API_KEY?.trim();
    if (apiKey) {
      config.headers = config.headers ?? {};
      config.headers["X-API-Key"] = apiKey;
    }
    return config;
  });

  // Response interceptor for error handling
  client.interceptors.response.use(
    (response) => response,
    (error) => {
      // Don't log 404s as errors globally - they are often expected "no data" states
      throw error;
    }
  );

  return client;
};

export const apiClient = createApiClient();

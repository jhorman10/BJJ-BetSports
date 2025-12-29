import axios, { AxiosInstance } from "axios";

// API base URL from environment or default
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Create configured Axios instance
 */
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: {
      "Content-Type": "application/json",
    },
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

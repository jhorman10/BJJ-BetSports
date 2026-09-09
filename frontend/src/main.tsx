/**
 * Application Entry Point
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { ThemeProvider, CssBaseline } from "@mui/material";
import { BrowserRouter as Router } from "react-router-dom";

import App from "./App";
import "./index.css";
import theme from "./theme";
import ErrorBoundary from "./presentation/components/common/ErrorBoundary";

const clearDevelopmentPwaState = async (): Promise<void> => {
  try {
    if (!import.meta.env.DEV || !("serviceWorker" in navigator)) {
      return;
    }

    const registrations = await navigator.serviceWorker.getRegistrations();
    await Promise.all(registrations.map((registration) => registration.unregister()));

    if (!("caches" in window)) {
      return;
    }

    const cacheKeys = await caches.keys();
    const deletions = cacheKeys.reduce<Promise<boolean>[]>((acc, key) => {
      if (key === "api-cache" || key.startsWith("workbox-")) {
        acc.push(caches.delete(key));
      }
      return acc;
    }, []);
    await Promise.all(deletions);
  } catch (error) {
    // Best-effort cleanup in development. Ignore failures to avoid unhandled rejections.
    console.warn("PWA cleanup failed:", error);
  }
};

void clearDevelopmentPwaState();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Router>
          <App />
        </Router>
      </ThemeProvider>
    </ErrorBoundary>
  </React.StrictMode>
);

/**
 * Application Entry Point
 */

import React from "react";
import ReactDOM from "react-dom/client";
import { ThemeProvider, CssBaseline } from "@mui/material";
import App from "./App";
import theme from "./theme";

import { BrowserRouter as Router } from "react-router-dom";

// Global styles
import "./index.css";

import ErrorBoundary from "./presentation/components/common/ErrorBoundary";

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

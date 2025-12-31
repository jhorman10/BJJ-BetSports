/**
 * Material UI Theme Configuration
 *
 * Custom dark theme with modern aesthetics for the prediction app.
 */

import { createTheme, ThemeOptions } from "@mui/material/styles";

const themeOptions: ThemeOptions = {
  palette: {
    mode: "dark",
    primary: {
      main: "#3b82f6", // Neon Blue
      light: "#60a5fa",
      dark: "#2563eb",
      contrastText: "#ffffff",
    },
    secondary: {
      main: "#10b981", // Neon Green
      light: "#34d399",
      dark: "#059669",
      contrastText: "#ffffff",
    },
    error: {
      main: "#ef4444",
    },
    warning: {
      main: "#f59e0b",
    },
    success: {
      main: "#10b981",
    },
    background: {
      default: "#0f172a", // Deep Blue
      paper: "rgba(30, 41, 59, 0.7)", // Glass Base
    },
    text: {
      primary: "#ffffff",
      secondary: "#94a3b8", // Slate 400
    },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: "2.5rem",
      fontWeight: 700,
      letterSpacing: "-0.02em",
      color: "#ffffff",
    },
    h2: {
      fontSize: "2rem",
      fontWeight: 600,
      letterSpacing: "-0.01em",
      color: "#ffffff",
    },
    h3: {
      fontSize: "1.5rem",
      fontWeight: 600,
      color: "#f8fafc",
    },
    h4: {
      fontSize: "1.25rem",
      fontWeight: 600,
      color: "#f8fafc",
    },
    h5: {
      fontSize: "1rem",
      fontWeight: 600,
      color: "#f1f5f9",
    },
    h6: {
      fontSize: "0.875rem",
      fontWeight: 600,
      color: "#f1f5f9",
    },
    body1: {
      fontSize: "1rem",
      lineHeight: 1.6,
      color: "#e2e8f0",
    },
    body2: {
      fontSize: "0.875rem",
      lineHeight: 1.5,
      color: "#cbd5e1",
    },
    button: {
      textTransform: "none",
      fontWeight: 600,
    },
  },
  shape: {
    borderRadius: 16, // Slightly more rounded for modern feel
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          backgroundColor: "#0f172a",
          backgroundImage:
            "radial-gradient(at 0% 0%, hsla(253,16%,7%,1) 0, transparent 50%), radial-gradient(at 50% 0%, hsla(225,39%,30%,1) 0, transparent 50%), radial-gradient(at 100% 0%, hsla(339,49%,30%,1) 0, transparent 50%)",
          backgroundAttachment: "fixed",
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          backgroundColor: "rgba(30, 41, 59, 0.7)",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          backgroundImage: "none",
          backgroundColor: "rgba(30, 41, 59, 0.7)",
          backdropFilter: "blur(12px)",
          border: "1px solid rgba(255, 255, 255, 0.08)",
          boxShadow: "0 8px 32px 0 rgba(0, 0, 0, 0.37)",
          transition: "transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out",
          "&:hover": {
            transform: "translateY(-2px)",
            boxShadow:
              "0 12px 40px 0 rgba(0, 0, 0, 0.5), 0 0 20px rgba(59, 130, 246, 0.1)", // Subtle blue glow on hover
          },
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          padding: "10px 24px",
          fontWeight: 600,
          textTransform: "none",
          transition: "all 0.2s ease-in-out",
        },
        contained: {
          boxShadow:
            "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        },
        containedPrimary: {
          background: "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)",
          "&:hover": {
            background: "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
            boxShadow: "0 0 15px rgba(59, 130, 246, 0.5)", // Blue neon glow
          },
        },
        containedSecondary: {
          background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
          "&:hover": {
            background: "linear-gradient(135deg, #059669 0%, #047857 100%)",
            boxShadow: "0 0 15px rgba(16, 185, 129, 0.5)", // Green neon glow
          },
        },
        outlined: {
          borderColor: "rgba(255, 255, 255, 0.2)",
          "&:hover": {
            borderColor: "rgba(255, 255, 255, 0.4)",
            backgroundColor: "rgba(255, 255, 255, 0.05)",
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          fontWeight: 500,
          backdropFilter: "blur(4px)",
        },
        filled: {
          backgroundColor: "rgba(255, 255, 255, 0.1)",
          border: "1px solid rgba(255, 255, 255, 0.05)",
        },
      },
    },
    MuiLinearProgress: {
      styleOverrides: {
        root: {
          borderRadius: 4,
          height: 8,
          backgroundColor: "rgba(255, 255, 255, 0.1)",
        },
        bar: {
          borderRadius: 4,
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          backgroundImage: "none",
          backgroundColor: "rgba(15, 23, 42, 0.95)", // Slightly more opaque for modals
          backdropFilter: "blur(16px)",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
        },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        root: {
          borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
        },
        head: {
          fontWeight: 600,
          color: "#94a3b8",
          backgroundColor: "rgba(15, 23, 42, 0.5)",
        },
      },
    },
  },
};

export const theme = createTheme(themeOptions);

export default theme;

/**
 * ErrorBoundary Component
 *
 * Catches JavaScript errors anywhere in their child component tree,
 * logs those errors, and displays a fallback UI instead of the component tree that crashed.
 */

import { Component, ErrorInfo, ReactNode } from "react";
import { Box, Typography, Button, Container, Paper } from "@mui/material";
import { ErrorOutline, Refresh } from "@mui/icons-material";

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI.
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render() {
    if (this.state.hasError) {
      return (
        <Box
          sx={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            bgcolor: "#0f172a",
            color: "white",
            p: 2,
          }}
        >
          <Container maxWidth="sm">
            <Paper
              sx={{
                p: 4,
                textAlign: "center",
                bgcolor: "rgba(30, 41, 59, 0.7)",
                backdropFilter: "blur(12px)",
                border: "1px solid rgba(239, 68, 68, 0.3)",
                borderRadius: 4,
              }}
            >
              <ErrorOutline sx={{ fontSize: 64, color: "#ef4444", mb: 2 }} />
              <Typography variant="h4" gutterBottom fontWeight={700}>
                ¡Ups! Algo salió mal
              </Typography>
              <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
                La aplicación ha experimentado un error inesperado al renderizar
                el contenido.
              </Typography>

              {this.state.error && (
                <Box
                  sx={{
                    mb: 4,
                    p: 2,
                    bgcolor: "rgba(0,0,0,0.3)",
                    borderRadius: 2,
                    textAlign: "left",
                    overflowX: "auto",
                  }}
                >
                  <Typography
                    variant="caption"
                    sx={{ fontFamily: "monospace", color: "#f87171" }}
                  >
                    {this.state.error.toString()}
                  </Typography>
                </Box>
              )}

              <Button
                variant="contained"
                startIcon={<Refresh />}
                onClick={this.handleReset}
                fullWidth
                sx={{
                  background:
                    "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)",
                }}
              >
                Recargar Aplicación
              </Button>
            </Paper>
          </Container>
        </Box>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

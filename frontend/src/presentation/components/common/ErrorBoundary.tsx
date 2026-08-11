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

  public componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error("Uncaught error:", error, errorInfo);
  }

  private handleReset = (): void => {
    this.setState({ hasError: false, error: null });
    window.location.reload();
  };

  public render(): ReactNode {
    if (this.state.hasError) {
      return (
        <Box
          sx={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background:
              "radial-gradient(circle at 50% 0%, #1e293b 0%, #0f172a 100%)",
            color: "white",
            p: 2,
          }}
        >
          <Container maxWidth="sm">
            <Paper
              elevation={24}
              sx={{
                p: 3, // Reduced padding
                textAlign: "center",
                background: "rgba(20, 25, 35, 0.9)", // More opaque
                backdropFilter: "blur(24px)",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                borderRadius: "20px",
                boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
              }}
            >
              <Box
                sx={{
                  display: "inline-flex",
                  p: 1.5,
                  borderRadius: "50%",
                  bgcolor: "rgba(239, 68, 68, 0.1)",
                  mb: 2,
                  boxShadow: "0 0 20px rgba(239, 68, 68, 0.2)",
                }}
              >
                <ErrorOutline sx={{ fontSize: 48, color: "#ef4444" }} />
              </Box>

              <Typography
                variant="h5"
                gutterBottom
                fontWeight={700}
                sx={{
                  color: "white",
                  mb: 1,
                }}
              >
                ¡Ups! Algo salió mal
              </Typography>

              <Typography
                variant="body2"
                sx={{ mb: 3, color: "white", opacity: 0.9 }}
              >
                La aplicación ha experimentado un error inesperado al renderizar
                el contenido.
              </Typography>

              {this.state.error && (
                <Box
                  sx={{
                    mb: 4,
                    p: 2.5,
                    bgcolor: "rgba(0,0,0,0.3)",
                    borderRadius: 3,
                    textAlign: "left",
                    overflowX: "auto",
                    border: "1px solid rgba(239, 68, 68, 0.2)",
                  }}
                >
                  <Typography
                    variant="caption"
                    sx={{
                      fontFamily: "monospace",
                      color: "white",
                      fontSize: "0.85rem",
                    }}
                  >
                    {this.state.error.toString()}
                  </Typography>
                </Box>
              )}

              <Button
                variant="contained"
                startIcon={<Refresh />}
                onClick={this.handleReset}
                size="large"
                fullWidth
                sx={{
                  py: 1.5,
                  fontSize: "1rem",
                  fontWeight: 700,
                  borderRadius: "12px",
                  background:
                    "linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)",
                  boxShadow: "0 0 20px rgba(59, 130, 246, 0.4)",
                  textTransform: "none",
                  transition: "all 0.3s ease",
                  "&:hover": {
                    transform: "translateY(-2px)",
                    boxShadow: "0 0 30px rgba(59, 130, 246, 0.6)",
                  },
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

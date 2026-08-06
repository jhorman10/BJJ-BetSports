import React, { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Container,
  Box,
  Typography,
  AppBar,
  Toolbar,
  Button,
} from "@mui/material";
import { SportsSoccer, GetApp, SmartToy, Calculate } from "@mui/icons-material";
import OfflineIndicator from "../../components/common/OfflineIndicator";
import { usePWAInstall } from "../../../hooks/usePWAInstall";
import { useBotStore } from "../../../application/stores/useBotStore";

interface MainLayoutProps {
  children: ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const { installPrompt, isInstalled, handleInstallClick } = usePWAInstall();
  const { trainingStatus } = useBotStore();
  const location = useLocation();

  const showBotIcon = trainingStatus !== "IDLE";

  return (
    <>
      <Box
        sx={{
          minHeight: "100vh",
          // Background handled by theme/CssBaseline
          bgcolor: "background.default",
        }}
      >
        {/* Navigation */}
        <AppBar
          position="static"
          elevation={0}
          className="glass-header"
          sx={{
            background: "transparent", // Handled by CSS class
          }}
        >
          <Toolbar>
            <SportsSoccer sx={{ mr: 2, color: "primary.main" }} />
            <Link to="/" style={{ textDecoration: "none", color: "inherit", display: "flex", alignItems: "center", flexGrow: 1 }}>
              <Typography
                variant="h6"
                component="h1"
                sx={{ fontWeight: 700 }}
              >
                BJJ - BetSports v2
              </Typography>
            </Link>

            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Link to="/" style={{ textDecoration: "none" }}>
                <Button
                  sx={{
                    color: location.pathname === "/" ? "primary.main" : "white",
                    fontWeight: location.pathname === "/" ? 700 : 400,
                    textTransform: "none"
                  }}
                  startIcon={<SportsSoccer />}
                >
                  Predicciones
                </Button>
              </Link>

              {showBotIcon && (
                <Link to="/bot" style={{ textDecoration: "none" }}>
                  <Button
                    sx={{
                      color: location.pathname === "/bot" ? "primary.main" : "white",
                      fontWeight: location.pathname === "/bot" ? 700 : 400,
                      textTransform: "none"
                    }}
                    startIcon={<SmartToy />}
                  >
                    Bot
                  </Button>
                </Link>
              )}

              <Link to="/parley-calculator" style={{ textDecoration: "none" }}>
                <Button
                  sx={{
                    color: location.pathname === "/parley-calculator" ? "primary.main" : "white",
                    fontWeight: location.pathname === "/parley-calculator" ? 700 : 400,
                    textTransform: "none"
                  }}
                  startIcon={<Calculate />}
                >
                  Calculadora
                </Button>
              </Link>
            </Box>

            {installPrompt && !isInstalled && (
              <Button
                variant="outlined"
                color="primary"
                size="small"
                startIcon={<GetApp />}
                onClick={handleInstallClick}
                sx={{ ml: 2 }}
              >
                Instalar App
              </Button>
            )}
          </Toolbar>
        </AppBar>

        {/* Main Content */}
        <Container maxWidth="xl" sx={{ py: 4 }} className="page-transition">
          {children}
        </Container>

        {/* Footer */}
        <Box
          component="footer"
          sx={{
            mt: 8,
            pt: 4,
            pb: 4,
            borderTop: "1px solid rgba(148, 163, 184, 0.1)",
            textAlign: "center",
          }}
        >
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            Modelos predictivos basados en datos estadísticos de alto
            rendimiento.
          </Typography>
          <Typography
            variant="caption"
            color="text.disabled"
            sx={{ display: "block", mb: 2, maxWidth: 800, mx: "auto" }}
          >
            Fuentes de datos: Football-Data.org, API-Football,
            Football-Data.co.uk, TheSportsDB, ESPN, ClubElo, Understat, FotMob,
            The Odds API, ScoreBat y OpenFootball. Las predicciones son
            probabilísticas y no garantizan resultados. Juegue con
            responsabilidad.
          </Typography>
          <Typography variant="caption" color="text.disabled" display="block">
            © 2025 BJJ - BetSports
          </Typography>
        </Box>
      </Box>

      {/* Offline Status Indicators */}
      <OfflineIndicator />
    </>
  );
};

export default MainLayout;

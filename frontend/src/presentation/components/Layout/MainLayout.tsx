import React, { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Box,
  Typography,
  AppBar,
  Toolbar,
  Button,
  useTheme,
  useMediaQuery,
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
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));

  const showBotIcon = trainingStatus !== "IDLE";

  return (
    <>
      <Box
        sx={{
          minHeight: "100dvh",
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
          <Toolbar sx={{ minHeight: { xs: 52, sm: 64 }, px: { xs: 1, sm: 2 } }}>
            <SportsSoccer sx={{ mr: { xs: 1, sm: 2 }, color: "primary.main", fontSize: { xs: "1.5rem", sm: "1.8rem" } }} />
            <Link to="/" style={{ textDecoration: "none", color: "inherit", display: "flex", alignItems: "center", flexGrow: 1, minWidth: 0 }}>
              <Typography
                variant="h6"
                component="h1"
                sx={{
                  fontWeight: 700,
                  fontSize: { xs: "0.85rem", sm: "1rem" },
                  whiteSpace: "nowrap",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                }}
              >
                BJJ - BetSports v2
              </Typography>
            </Link>

            <Box sx={{ display: "flex", alignItems: "center", gap: { xs: 0.5, sm: 1 }, flexShrink: 0 }}>
              <Link to="/" style={{ textDecoration: "none" }}>
                <Button
                  sx={{
                    color: location.pathname === "/" ? "primary.main" : "white",
                    fontWeight: location.pathname === "/" ? 700 : 400,
                    textTransform: "none",
                    minWidth: 0,
                    px: { xs: 1, sm: 1.5 },
                  }}
                  startIcon={!isMobile ? <SportsSoccer /> : undefined}
                >
                  {isMobile ? <SportsSoccer /> : "Predicciones"}
                </Button>
              </Link>

              {showBotIcon && (
                <Link to="/bot" style={{ textDecoration: "none" }}>
                  <Button
                    sx={{
                      color: location.pathname === "/bot" ? "primary.main" : "white",
                      fontWeight: location.pathname === "/bot" ? 700 : 400,
                      textTransform: "none",
                      minWidth: 0,
                      px: { xs: 1, sm: 1.5 },
                    }}
                    startIcon={!isMobile ? <SmartToy /> : undefined}
                  >
                    {isMobile ? <SmartToy /> : "Bot"}
                  </Button>
                </Link>
              )}

              <Link to="/parley-calculator" style={{ textDecoration: "none" }}>
                <Button
                  sx={{
                    color: location.pathname === "/parley-calculator" ? "primary.main" : "white",
                    fontWeight: location.pathname === "/parley-calculator" ? 700 : 400,
                    textTransform: "none",
                    minWidth: 0,
                    px: { xs: 1, sm: 1.5 },
                  }}
                  startIcon={!isMobile ? <Calculate /> : undefined}
                >
                  {isMobile ? <Calculate /> : "Calculadora"}
                </Button>
              </Link>
            </Box>

            {installPrompt && !isInstalled && (
              <Button
                variant="outlined"
                color="primary"
                size="small"
                onClick={handleInstallClick}
                sx={{ ml: { xs: 0.5, sm: 2 }, minWidth: 0, px: { xs: 1, sm: 1.5 } }}
                startIcon={!isMobile ? <GetApp /> : undefined}
              >
                {isMobile ? <GetApp /> : "Instalar App"}
              </Button>
            )}
          </Toolbar>
        </AppBar>

        {/* Main Content */}
        <Box
          component="main"
          sx={{
            maxWidth: "xl",
            mx: "auto",
            py: { xs: 2, sm: 4 },
            px: { xs: 0, sm: 2, md: 3 },
            width: "100%",
          }}
          className="page-transition"
        >
          {children}
        </Box>

        {/* Footer */}
        <Box
          component="footer"
          sx={{
            mt: { xs: 4, sm: 8 },
            pt: { xs: 2, sm: 4 },
            pb: { xs: 2, sm: 4 },
            px: { xs: 2, sm: 0 },
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

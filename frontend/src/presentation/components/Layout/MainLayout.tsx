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
          <Toolbar sx={{ minHeight: { xs: 52, sm: 64 }, px: { xs: 1, sm: 2 }, overflow: "hidden" }}>
            <SportsSoccer sx={{ mr: { xs: 0.5, sm: 2 }, color: "primary.main", fontSize: { xs: "1.3rem", sm: "1.8rem" }, flexShrink: 0 }} />
            <Link to="/" style={{ textDecoration: "none", color: "inherit", display: "flex", alignItems: "center", minWidth: 0, overflow: "hidden" }}>
              <Typography
                variant="h6"
                component="h1"
                noWrap
                sx={{
                  fontWeight: 700,
                  fontSize: { xs: "0.8rem", sm: "1rem" },
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  minWidth: 0,
                }}
              >
                BJJ BetSports
              </Typography>
            </Link>

            <Box sx={{ display: "flex", alignItems: "center", gap: { xs: 0.25, sm: 1 }, flexShrink: 0, ml: "auto" }}>
              <Link to="/" style={{ textDecoration: "none" }}>
                <Button
                  sx={{
                    color: location.pathname === "/" ? "primary.main" : "white",
                    fontWeight: location.pathname === "/" ? 700 : 400,
                    textTransform: "none",
                    minWidth: 0,
                    px: { xs: 0.5, sm: 1.5 },
                    gap: 0.5,
                  }}
                >
                  <SportsSoccer sx={{ fontSize: { xs: "1.1rem", sm: "1.25rem" } }} />
                  <Box component="span" sx={{ display: { xs: "none", sm: "inline" } }}>Predicciones</Box>
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
                      px: { xs: 0.5, sm: 1.5 },
                      gap: 0.5,
                    }}
                  >
                    <SmartToy sx={{ fontSize: { xs: "1.1rem", sm: "1.25rem" } }} />
                    <Box component="span" sx={{ display: { xs: "none", sm: "inline" } }}>Bot</Box>
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
                    px: { xs: 0.5, sm: 1.5 },
                    gap: 0.5,
                  }}
                >
                  <Calculate sx={{ fontSize: { xs: "1.1rem", sm: "1.25rem" } }} />
                  <Box component="span" sx={{ display: { xs: "none", sm: "inline" } }}>Calculadora</Box>
                </Button>
              </Link>
            </Box>

            {installPrompt && !isInstalled && (
              <Button
                variant="outlined"
                color="primary"
                size="small"
                onClick={handleInstallClick}
                sx={{ ml: { xs: 0.25, sm: 2 }, minWidth: 0, px: { xs: 0.5, sm: 1.5 }, flexShrink: 0 }}
              >
                <GetApp sx={{ fontSize: "1.1rem" }} />
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

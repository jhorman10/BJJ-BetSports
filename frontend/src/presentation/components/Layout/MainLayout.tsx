import React, { ReactNode, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Container,
  Box,
  Typography,
  AppBar,
  Toolbar,
  Button,
  IconButton,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Divider,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import {
  SportsSoccer,
  GetApp,
  SmartToy,
  Calculate,
  Menu as MenuIcon,
  Close,
} from "@mui/icons-material";

import OfflineIndicator from "../../components/common/OfflineIndicator";
import { usePWAInstall } from "../../../hooks/usePWAInstall";
import { useBotStore } from "../../../application/stores/useBotStore";

interface MainLayoutProps {
  children: ReactNode;
}

const NAV_ITEMS = [
  { path: "/", label: "Predicciones", icon: SportsSoccer },
  { path: "/parley-calculator", label: "Calculadora", icon: Calculate },
];

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const { installPrompt, isInstalled, handleInstallClick } = usePWAInstall();
  const { trainingStatus } = useBotStore();
  const location = useLocation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const [drawerOpen, setDrawerOpen] = useState(false);

  const showBotIcon = trainingStatus !== "IDLE";

  const isActive = (path: string): boolean => location.pathname === path;

  const navContent = (
    <>
      {NAV_ITEMS.map((item) => (
        <ListItem key={item.path} disablePadding>
          <ListItemButton
            component={Link}
            to={item.path}
            selected={isActive(item.path)}
            onClick={() => setDrawerOpen(false)}
            sx={{
              borderRadius: 2,
              mx: 1,
              mb: 0.5,
              color: isActive(item.path) ? "primary.main" : "white",
              "&.Mui-selected": {
                bgcolor: "rgba(59, 130, 246, 0.1)",
              },
            }}
          >
            <ListItemIcon sx={{ color: "inherit", minWidth: 40 }}>
              <item.icon />
            </ListItemIcon>
            <ListItemText
              primary={item.label}
              primaryTypographyProps={{ fontWeight: isActive(item.path) ? 700 : 400 }}
            />
          </ListItemButton>
        </ListItem>
      ))}
      {showBotIcon && (
        <ListItem disablePadding>
          <ListItemButton
            component={Link}
            to="/bot"
            selected={isActive("/bot")}
            onClick={() => setDrawerOpen(false)}
            sx={{
              borderRadius: 2,
              mx: 1,
              mb: 0.5,
              color: isActive("/bot") ? "primary.main" : "white",
              "&.Mui-selected": {
                bgcolor: "rgba(59, 130, 246, 0.1)",
              },
            }}
          >
            <ListItemIcon sx={{ color: "inherit", minWidth: 40 }}>
              <SmartToy />
            </ListItemIcon>
            <ListItemText
              primary="Bot"
              primaryTypographyProps={{ fontWeight: isActive("/bot") ? 700 : 400 }}
            />
          </ListItemButton>
        </ListItem>
      )}
    </>
  );

  return (
    <>
      <Box
        sx={{
          minHeight: "100vh",
          bgcolor: "background.default",
        }}
      >
        {/* Navigation */}
        <AppBar
          position="static"
          elevation={0}
          className="glass-header"
          sx={{
            background: "transparent",
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

            {/* Desktop nav */}
            {!isMobile && (
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                {NAV_ITEMS.map((item) => (
                  <Link key={item.path} to={item.path} style={{ textDecoration: "none" }}>
                    <Button
                      sx={{
                        color: isActive(item.path) ? "primary.main" : "white",
                        fontWeight: isActive(item.path) ? 700 : 400,
                        textTransform: "none",
                      }}
                      startIcon={<item.icon />}
                    >
                      {item.label}
                    </Button>
                  </Link>
                ))}
                {showBotIcon && (
                  <Link to="/bot" style={{ textDecoration: "none" }}>
                    <Button
                      sx={{
                        color: isActive("/bot") ? "primary.main" : "white",
                        fontWeight: isActive("/bot") ? 700 : 400,
                        textTransform: "none",
                      }}
                      startIcon={<SmartToy />}
                    >
                      Bot
                    </Button>
                  </Link>
                )}
              </Box>
            )}

            {/* Install button */}
            {installPrompt && !isInstalled && (
              <Button
                variant="outlined"
                color="primary"
                size="small"
                startIcon={<GetApp />}
                onClick={handleInstallClick}
                sx={{ ml: 2, display: { xs: "none", sm: "flex" } }}
              >
                Instalar App
              </Button>
            )}

            {/* Mobile hamburger */}
            {isMobile && (
              <IconButton
                color="inherit"
                edge="end"
                onClick={() => setDrawerOpen(true)}
                sx={{ ml: 1 }}
              >
                <MenuIcon />
              </IconButton>
            )}
          </Toolbar>
        </AppBar>

        {/* Mobile drawer */}
        <Drawer
          anchor="right"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          PaperProps={{
            sx: {
              width: 280,
              bgcolor: "rgba(15, 23, 42, 0.98)",
              backdropFilter: "blur(20px)",
              borderLeft: "1px solid rgba(255, 255, 255, 0.08)",
            },
          }}
        >
          <Box sx={{ p: 2, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Typography variant="h6" fontWeight={700}>
              Menú
            </Typography>
            <IconButton onClick={() => setDrawerOpen(false)} color="inherit">
              <Close />
            </IconButton>
          </Box>
          <Divider sx={{ borderColor: "rgba(255, 255, 255, 0.08)" }} />
          <List sx={{ pt: 1 }}>{navContent}</List>
          {installPrompt && !isInstalled && (
            <Box sx={{ px: 2, mt: 2 }}>
              <Button
                fullWidth
                variant="outlined"
                color="primary"
                startIcon={<GetApp />}
                onClick={() => {
                  handleInstallClick();
                  setDrawerOpen(false);
                }}
              >
                Instalar App
              </Button>
            </Box>
          )}
        </Drawer>

        {/* Main Content */}
        <Container maxWidth="xl" sx={{ py: { xs: 2, sm: 4 } }} className="page-transition">
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
            px: { xs: 2, sm: 4 },
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

/**
 * LeagueSelector Component
 *
 * Modern, compact dropdown selectors for choosing country and league.
 */

import React from "react";
import {
  Box,
  Typography,
  CircularProgress,
  Card,
  Avatar,
  Stack,
  SelectChangeEvent,
  Chip,
  ToggleButton,
} from "@mui/material";
import { SportsScore, LiveTv } from "@mui/icons-material";
import { Country, League } from "../../types";
import CountrySelect from "./CountrySelect";
import LeagueSelect from "./LeagueSelect";
import {
  COUNTRY_DATA,
  MENU_PROPS,
  SELECT_STYLES,
  getLeagueName,
} from "./constants";

export interface LeagueSelectorProps {
  countries: Country[];
  selectedCountry: Country | null;
  selectedLeague: League | null;
  onCountryChange: (country: Country | null) => void;
  onLeagueChange: (league: League | null) => void;
  showLive: boolean;
  onLiveToggle: () => void;
  loading?: boolean;
}

const LeagueSelector: React.FC<LeagueSelectorProps> = ({
  countries,
  selectedCountry,
  selectedLeague,
  onCountryChange,
  onLeagueChange,
  showLive,
  onLiveToggle,
  loading = false,
}) => {
  const handleCountryChange = (event: SelectChangeEvent<string>) => {
    const countryName = event.target.value;

    if (!countryName) {
      onCountryChange(null);
      return;
    }
    const country = countries.find((c) => c.name === countryName) || null;
    onCountryChange(country);
  };

  const handleLeagueChange = (event: SelectChangeEvent<string>) => {
    const leagueId = event.target.value;
    if (!leagueId || !selectedCountry) {
      onLeagueChange(null);
      return;
    }
    const league =
      selectedCountry.leagues.find((l) => l.id === leagueId) || null;
    onLeagueChange(league);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" py={4}>
        <CircularProgress size={32} />
        <Typography ml={2} color="text.secondary" variant="body2">
          Cargando ligas...
        </Typography>
      </Box>
    );
  }

  return (
    <Card
      elevation={0}
      sx={{
        mb: 4,
        p: 3,
        background:
          "linear-gradient(145deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%)",
        border: "1px solid rgba(99, 102, 241, 0.15)",
        borderRadius: 3,
        backdropFilter: "blur(10px)",
      }}
    >
      <Stack spacing={3}>
        {/* Header */}
        <Box display="flex" alignItems="center" gap={2}>
          <Avatar
            sx={{
              width: 40,
              height: 40,
              background: "linear-gradient(135deg, #6366f1 0%, #10b981 100%)",
            }}
          >
            <SportsScore fontSize="small" />
          </Avatar>
          <Box>
            <Typography variant="subtitle1" fontWeight={600}>
              Selecciona una Liga
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Elige el país y la liga para ver las predicciones
            </Typography>
          </Box>

          {/* Live Toggle - Top Right */}
          <ToggleButton
            value="check"
            selected={showLive}
            onChange={onLiveToggle}
            size="small"
            color="error"
            sx={{
              borderRadius: 2,
              ml: "auto !important",
              border: "1px solid rgba(239, 68, 68, 0.5)",
              "&.Mui-selected": {
                backgroundColor: "rgba(239, 68, 68, 0.2)",
                color: "#ef4444",
                "&:hover": {
                  backgroundColor: "rgba(239, 68, 68, 0.3)",
                },
              },
            }}
          >
            <LiveTv fontSize="small" sx={{ mr: 1 }} />
            EN VIVO
          </ToggleButton>
        </Box>

        {/* Selectors Row */}
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          <CountrySelect
            countries={countries}
            selectedCountryName={selectedCountry?.name || ""}
            onCountryChange={handleCountryChange}
            countryData={COUNTRY_DATA}
            selectStyles={SELECT_STYLES}
            menuProps={MENU_PROPS}
          />

          <LeagueSelect
            leagues={selectedCountry?.leagues || []}
            selectedLeagueId={selectedLeague?.id || ""}
            selectedCountry={selectedCountry}
            onLeagueChange={handleLeagueChange}
            selectStyles={SELECT_STYLES}
            menuProps={MENU_PROPS}
          />
        </Stack>

        {/* Selected League Badge */}
        {selectedLeague && (
          <Box
            display="flex"
            alignItems="center"
            gap={1.5}
            p={1.5}
            borderRadius={2}
            sx={{
              background:
                "linear-gradient(90deg, rgba(99, 102, 241, 0.15) 0%, rgba(16, 185, 129, 0.1) 100%)",
              border: "1px solid rgba(99, 102, 241, 0.2)",
            }}
          >
            <Box
              sx={{
                width: 32,
                height: 32,
                borderRadius: 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: "linear-gradient(135deg, #6366f1 0%, #10b981 100%)",
              }}
            >
              <SportsScore fontSize="small" />
            </Box>
            <Box sx={{ flex: 1 }}>
              <Typography variant="body2" fontWeight={600}>
                {getLeagueName(selectedLeague.name)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {COUNTRY_DATA[selectedLeague.country]?.name ||
                  selectedLeague.country}
              </Typography>
            </Box>
            <Chip
              label="Seleccionado"
              size="small"
              sx={{
                height: 24,
                backgroundColor: "rgba(16, 185, 129, 0.2)",
                color: "#34d399",
                fontWeight: 600,
                fontSize: "0.7rem",
              }}
            />
          </Box>
        )}
      </Stack>
    </Card>
  );
};

export default LeagueSelector;

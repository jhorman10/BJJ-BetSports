/**
 * LeagueSelector Component
 *
 * Modern, compact dropdown selectors for choosing country and league.
 */

import React from "react";
import {
  Box,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Typography,
  Chip,
  CircularProgress,
  Card,
  Avatar,
  Stack,
} from "@mui/material";
import { SportsScore, KeyboardArrowDown } from "@mui/icons-material";
import { Country, League } from "../../types";

interface LeagueSelectorProps {
  countries: Country[];
  selectedCountry: Country | null;
  selectedLeague: League | null;
  onCountryChange: (country: Country | null) => void;
  onLeagueChange: (league: League | null) => void;
  loading?: boolean;
}

// Country flag emojis and Spanish names
const countryData: Record<string, { flag: string; name: string }> = {
  England: { flag: "🏴󠁧󠁢󠁥󠁮󠁧󠁿", name: "Inglaterra" },
  Spain: { flag: "🇪🇸", name: "España" },
  Germany: { flag: "🇩🇪", name: "Alemania" },
  Italy: { flag: "🇮🇹", name: "Italia" },
  France: { flag: "🇫🇷", name: "Francia" },
  Netherlands: { flag: "🇳🇱", name: "Países Bajos" },
  Belgium: { flag: "🇧🇪", name: "Bélgica" },
  Portugal: { flag: "🇵🇹", name: "Portugal" },
  Turkey: { flag: "🇹🇷", name: "Turquía" },
  Greece: { flag: "🇬🇷", name: "Grecia" },
  Scotland: { flag: "🏴󠁧󠁢󠁳󠁣󠁴󠁿", name: "Escocia" },
  Europe: { flag: "🇪🇺", name: "Europa" },
};

const LeagueSelector: React.FC<LeagueSelectorProps> = ({
  countries,
  selectedCountry,
  selectedLeague,
  onCountryChange,
  onLeagueChange,
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

  const selectStyles = {
    height: 48,
    borderRadius: 2,
    backgroundColor: "rgba(15, 23, 42, 0.6)",
    backdropFilter: "blur(10px)",
    "& .MuiOutlinedInput-notchedOutline": {
      borderColor: "rgba(99, 102, 241, 0.3)",
      transition: "all 0.2s ease",
    },
    "&:hover .MuiOutlinedInput-notchedOutline": {
      borderColor: "rgba(99, 102, 241, 0.6)",
    },
    "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
      borderColor: "#6366f1",
      borderWidth: 2,
    },
    "& .MuiSelect-select": {
      display: "flex",
      alignItems: "center",
      gap: 1.5,
      py: 1.5,
    },
    "& .MuiSelect-icon": {
      color: "#6366f1",
      transition: "transform 0.2s ease",
    },
    "&.Mui-focused .MuiSelect-icon": {
      transform: "rotate(180deg)",
    },
  };

  const menuProps = {
    PaperProps: {
      sx: {
        mt: 1,
        borderRadius: 2,
        backgroundColor: "rgba(30, 41, 59, 0.98)",
        backdropFilter: "blur(20px)",
        border: "1px solid rgba(99, 102, 241, 0.2)",
        boxShadow: "0 20px 40px rgba(0, 0, 0, 0.4)",
        maxHeight: 320,
        "& .MuiMenuItem-root": {
          borderRadius: 1,
          mx: 1,
          my: 0.5,
          transition: "all 0.15s ease",
          "&:hover": {
            backgroundColor: "rgba(99, 102, 241, 0.15)",
          },
          "&.Mui-selected": {
            backgroundColor: "rgba(99, 102, 241, 0.25)",
            "&:hover": {
              backgroundColor: "rgba(99, 102, 241, 0.3)",
            },
          },
        },
      },
    },
  };

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
        </Box>

        {/* Selectors Row */}
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          {/* Country Selector */}
          <FormControl sx={{ flex: 1, minWidth: 180 }} size="small">
            <InputLabel
              id="country-select-label"
              sx={{
                color: "text.secondary",
                "&.Mui-focused": { color: "#6366f1" },
              }}
            >
              País
            </InputLabel>
            <Select
              labelId="country-select-label"
              value={selectedCountry?.name || ""}
              label="País"
              onChange={handleCountryChange}
              IconComponent={KeyboardArrowDown}
              MenuProps={menuProps}
              sx={selectStyles}
            >
              <MenuItem value="" sx={{ opacity: 0.7 }}>
                <Typography variant="body2" color="text.secondary">
                  Seleccionar país...
                </Typography>
              </MenuItem>
              {countries.map((country) => (
                <MenuItem key={country.name} value={country.name}>
                  <Box
                    display="flex"
                    alignItems="center"
                    gap={1.5}
                    width="100%"
                  >
                    <Typography fontSize="1.2rem">
                      {countryData[country.name]?.flag || "🌍"}
                    </Typography>
                    <Typography
                      variant="body2"
                      fontWeight={500}
                      sx={{ flex: 1 }}
                    >
                      {countryData[country.name]?.name || country.name}
                    </Typography>
                    <Chip
                      label={country.leagues.length}
                      size="small"
                      sx={{
                        height: 20,
                        fontSize: "0.7rem",
                        fontWeight: 600,
                        backgroundColor: "rgba(99, 102, 241, 0.2)",
                        color: "#818cf8",
                      }}
                    />
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* League Selector */}
          <FormControl
            sx={{ flex: 1, minWidth: 200 }}
            size="small"
            disabled={!selectedCountry}
          >
            <InputLabel
              id="league-select-label"
              sx={{
                color: "text.secondary",
                "&.Mui-focused": { color: "#6366f1" },
              }}
            >
              Liga
            </InputLabel>
            <Select
              labelId="league-select-label"
              value={selectedLeague?.id || ""}
              label="Liga"
              onChange={handleLeagueChange}
              IconComponent={KeyboardArrowDown}
              MenuProps={menuProps}
              sx={{
                ...selectStyles,
                "&.Mui-disabled": {
                  backgroundColor: "rgba(15, 23, 42, 0.4)",
                  "& .MuiOutlinedInput-notchedOutline": {
                    borderColor: "rgba(148, 163, 184, 0.1)",
                  },
                },
              }}
            >
              <MenuItem value="" sx={{ opacity: 0.7 }}>
                <Typography variant="body2" color="text.secondary">
                  {selectedCountry
                    ? "Seleccionar liga..."
                    : "Primero selecciona un país"}
                </Typography>
              </MenuItem>
              {selectedCountry?.leagues.map((league) => (
                <MenuItem key={league.id} value={league.id}>
                  <Box display="flex" alignItems="center" gap={1.5}>
                    <Box
                      sx={{
                        width: 8,
                        height: 8,
                        borderRadius: "50%",
                        background:
                          "linear-gradient(135deg, #6366f1 0%, #10b981 100%)",
                      }}
                    />
                    <Typography variant="body2" fontWeight={500}>
                      {league.name}
                    </Typography>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
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
                {selectedLeague.name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {countryData[selectedLeague.country]?.name ||
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

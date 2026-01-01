import React from "react";
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Box,
  SelectChangeEvent,
  Chip,
} from "@mui/material";
import { KeyboardArrowDown } from "@mui/icons-material";
import { Country } from "../../../types";

interface CountrySelectProps {
  countries: Country[];
  selectedCountryName: string;
  onCountryChange: (event: SelectChangeEvent<string>) => void;
  countryData: Record<string, { flag: string; name: string }>;
  selectStyles: any;
  menuProps: any;
}

const CountrySelect: React.FC<CountrySelectProps> = ({
  countries,
  selectedCountryName,
  onCountryChange,
  countryData,
  selectStyles,
  menuProps,
}) => {
  return (
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
        value={
          countries.some((c) => c.name === selectedCountryName)
            ? selectedCountryName
            : ""
        }
        label="País"
        onChange={onCountryChange}
        IconComponent={KeyboardArrowDown}
        MenuProps={menuProps}
        sx={selectStyles}
      >
        <MenuItem value="">
          <Typography variant="body2" color="text.secondary">
            Seleccionar país...
          </Typography>
        </MenuItem>

        {countries.map((country) => (
          <MenuItem key={country.name} value={country.name}>
            <Box display="flex" alignItems="center" gap={1.5} width="100%">
              <Typography fontSize="1.2rem">
                {countryData[country.name]?.flag || "🌍"}
              </Typography>
              <Typography variant="body2" fontWeight={500} sx={{ flex: 1 }}>
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
  );
};

export default CountrySelect;

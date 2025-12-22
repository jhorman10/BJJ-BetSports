import React from "react";
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Typography,
  Box,
  SelectChangeEvent,
} from "@mui/material";
import { KeyboardArrowDown } from "@mui/icons-material";
import { League, Country } from "../../types";

interface LeagueSelectProps {
  leagues: League[];
  selectedLeagueId: string;
  selectedCountry: Country | null;
  onLeagueChange: (event: SelectChangeEvent<string>) => void;
  selectStyles: any;
  menuProps: any;
}

const LeagueSelect: React.FC<LeagueSelectProps> = ({
  leagues,
  selectedLeagueId,
  selectedCountry,
  onLeagueChange,
  selectStyles,
  menuProps,
}) => {
  return (
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
        value={selectedLeagueId}
        label="Liga"
        onChange={onLeagueChange}
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
        {leagues.map((league) => (
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
  );
};

export default LeagueSelect;

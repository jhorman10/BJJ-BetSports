import React from "react";
import {
  Box,
  Typography,
  ToggleButtonGroup,
  ToggleButton,
  Chip,
} from "@mui/material";
import { SportsBasketball } from "@mui/icons-material";
import { BasketballConference } from "../../../types";

interface BasketballTeamSelectorProps {
  conferences: BasketballConference[];
  selectedConference: string | null;
  onSelect: (conferenceId: string | null) => void;
}

const BasketballTeamSelector: React.FC<BasketballTeamSelectorProps> = ({
  conferences,
  selectedConference,
  onSelect,
}) => {
  return (
    <Box mb={3}>
      <Box display="flex" alignItems="center" gap={1} mb={1}>
        <SportsBasketball sx={{ color: "#f59e0b", fontSize: 24 }} />
        <Typography variant="subtitle1" fontWeight={600} color="text.secondary">
          Filtrar por conferencia
        </Typography>
      </Box>
      <ToggleButtonGroup
        value={selectedConference}
        exclusive
        onChange={(_, value) => onSelect(value === "all" ? null : value)}
        sx={{
          flexWrap: "wrap",
          gap: 0.5,
          "& .MuiToggleButton-root": {
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "12px",
            px: 2,
            py: 1,
            color: "rgba(255,255,255,0.6)",
            textTransform: "none",
            fontWeight: 600,
            "&.Mui-selected": {
              bgcolor: "rgba(99,102,241,0.2)",
              color: "#a5b4fc",
              borderColor: "rgba(99,102,241,0.4)",
            },
            "&:hover": {
              bgcolor: "rgba(255,255,255,0.05)",
            },
          },
        }}
      >
        <ToggleButton value="all">
          Todos
        </ToggleButton>
        {conferences.map((conf) => (
          <ToggleButton key={conf.id} value={conf.id}>
            {conf.name}
            <Chip
              label={conf.teams.length}
              size="small"
              sx={{
                ml: 1,
                height: 20,
                fontSize: "0.7rem",
                bgcolor: "rgba(255,255,255,0.1)",
                color: "rgba(255,255,255,0.7)",
              }}
            />
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
    </Box>
  );
};

export default BasketballTeamSelector;

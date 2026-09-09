import React from "react";
import { Box, Typography } from "@mui/material";

import { SuggestedPick } from "../../../../types";
import { Match } from "../../../../domain/entities/match";

import { PickRow } from "./PickRow";

interface PicksScrollListProps {
  filteredPicks: SuggestedPick[];
  match?: Match;
}

const PicksScrollList: React.FC<PicksScrollListProps> = ({ filteredPicks, match }) => (
  <Box
    sx={{
      maxHeight: { xs: "50vh", md: "400px" },
      minHeight: "150px",
      overflowY: "auto",
      pr: 1,
      "&::-webkit-scrollbar": { width: "6px" },
      "&::-webkit-scrollbar-track": { background: "rgba(255, 255, 255, 0.05)" },
      "&::-webkit-scrollbar-thumb": { background: "rgba(255, 255, 255, 0.2)", borderRadius: "4px" },
      "&::-webkit-scrollbar-thumb:hover": { background: "rgba(255, 255, 255, 0.3)" },
    }}
  >
    {filteredPicks.length > 0 ? (
      filteredPicks.map((pick) => (
        <PickRow key={pick.market_type} pick={pick} match={match} />
      ))
    ) : (
      <Box py={4} textAlign="center">
        <Typography variant="caption" color="text.secondary">
          No hay picks en esta categoría
        </Typography>
      </Box>
    )}
  </Box>
);

export default PicksScrollList;

import React from "react";
import { Box, Typography } from "@mui/material";
import { Flag } from "@mui/icons-material";

import { LiveMatchRaw } from "../../../../utils/matchMatching";

const CardBadge: React.FC<{ color: string }> = ({ color }) => (
  <Box
    sx={{
      width: 8,
      height: 8,
      backgroundColor: color,
      borderRadius: "2px",
      boxShadow: `0 0 8px ${color}`,
    }}
  />
);

interface StatItemProps {
  label: string;
  home: number;
  away: number;
  badgeColor: string;
  icon?: React.ReactNode;
}

const StatItem: React.FC<StatItemProps> = ({ label, home, away, badgeColor, icon }) => (
  <>
    <Box display="flex" flexDirection="column" alignItems="center">
      <Box display="flex" alignItems="center" gap={0.5} mb={0.2}>
        {icon || <CardBadge color={badgeColor} />}
        <Typography
          variant="caption"
          color="rgba(255,255,255,0.4)"
          fontSize="0.6rem"
          fontWeight={700}
          letterSpacing={0.5}
        >
          {label}
        </Typography>
      </Box>
      <Typography variant="body2" fontWeight={700} color="white" letterSpacing={1}>
        {home} : {away}
      </Typography>
    </Box>
    <Box sx={{ width: "1px", height: "20px", bgcolor: "rgba(255,255,255,0.08)" }} />
  </>
);

interface StatsBarProps {
  match: LiveMatchRaw;
}

export const StatsBar: React.FC<StatsBarProps> = ({ match }) => (
  <Box
    sx={{
      background: "rgba(15, 23, 42, 0.4)",
      borderRadius: "16px",
      py: 1.5,
      px: 2,
      border: "1px solid rgba(255,255,255,0.05)",
      display: "flex",
      justifyContent: "space-around",
      alignItems: "center",
      mt: "auto",
    }}
  >
    <StatItem
      label="CÓRNERS"
      home={match.home_corners}
      away={match.away_corners}
      badgeColor="transparent"
      icon={<Flag sx={{ fontSize: 10, color: "rgba(255,255,255,0.4)" }} />}
    />
    <StatItem
      label="AMARILLAS"
      home={match.home_yellow_cards}
      away={match.away_yellow_cards}
      badgeColor="#facc15"
    />
    <StatItem
      label="ROJAS"
      home={match.home_red_cards}
      away={match.away_red_cards}
      badgeColor="#ef4444"
    />
  </Box>
);

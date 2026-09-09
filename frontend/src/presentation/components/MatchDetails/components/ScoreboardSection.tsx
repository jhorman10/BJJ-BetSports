import React from "react";
import { Box, Typography } from "@mui/material";
import { SportsSoccer } from "@mui/icons-material";

import { LiveMatchRaw } from "../../../../utils/matchMatching";
import { cleanTeamName } from "../../../../utils/teamUtils";
import { TeamLogo } from "../../common/TeamLogo";

interface TeamSectionProps {
  logoUrl?: string;
  shortName?: string;
  team: string;
}

const TeamSection: React.FC<TeamSectionProps> = ({ logoUrl, shortName, team }) => (
  <Box
    display="flex"
    flexDirection="column"
    alignItems="center"
    justifyContent="center"
    zIndex={2}
  >
    <Box
      sx={{
        position: "relative",
        mb: 1,
        filter: "drop-shadow(0 6px 8px rgba(0,0,0,0.4))",
      }}
    >
      {logoUrl ? (
        <TeamLogo
          src={logoUrl}
          alt={cleanTeamName(shortName || team)}
          width={42}
          height={42}
          sx={{
            transition: "transform 0.3s",
            "&:hover": { transform: "scale(1.1)" },
          }}
        />
      ) : (
        <SportsSoccer sx={{ fontSize: 36, color: "rgba(255,255,255,0.1)" }} />
      )}
    </Box>
    <Typography
      variant="body2"
      fontWeight={700}
      color="white"
      align="center"
      sx={{
        lineHeight: 1.2,
        display: "-webkit-box",
        WebkitLineClamp: 2,
        WebkitBoxOrient: "vertical",
        overflow: "hidden",
        fontSize: "0.85rem",
        textShadow: "0 2px 4px rgba(0,0,0,0.8)",
        px: 1,
        letterSpacing: "0.2px",
      }}
    >
      {cleanTeamName(shortName || team)}
    </Typography>
  </Box>
);

interface ScoreboardSectionProps {
  match: LiveMatchRaw;
}

export const ScoreboardSection: React.FC<ScoreboardSectionProps> = ({ match }) => (
  <Box
    display="grid"
    gridTemplateColumns="1fr auto 1fr"
    alignItems="center"
    mb={3}
    position="relative"
  >
    <TeamSection logoUrl={match.home_logo_url} shortName={match.home_short_name} team={match.home_team} />

    <Box display="flex" alignItems="center" justifyContent="center" sx={{ px: 1, zIndex: 2 }}>
      <Typography
        variant="h3"
        fontWeight={800}
        color="white"
        sx={{
          fontSize: "1.5rem",
          lineHeight: 1,
          textShadow: "0 0 20px rgba(255,255,255,0.15), 0 4px 10px rgba(0,0,0,0.5)",
          fontFeatureSettings: "'tnum'",
        }}
      >
        {match.home_score}
      </Typography>
      <Typography
        variant="h4"
        sx={{
          mx: 1.5,
          color: "rgba(255,255,255,0.15)",
          fontWeight: 200,
          fontSize: "1.25rem",
          lineHeight: 1,
          mb: 0.5,
        }}
      >
        -
      </Typography>
      <Typography
        variant="h3"
        fontWeight={800}
        color="white"
        sx={{
          fontSize: "1.5rem",
          lineHeight: 1,
          textShadow: "0 0 20px rgba(255,255,255,0.15), 0 4px 10px rgba(0,0,0,0.5)",
          fontFeatureSettings: "'tnum'",
        }}
      >
        {match.away_score}
      </Typography>
    </Box>

    <TeamSection logoUrl={match.away_logo_url} shortName={match.away_short_name} team={match.away_team} />
  </Box>
);

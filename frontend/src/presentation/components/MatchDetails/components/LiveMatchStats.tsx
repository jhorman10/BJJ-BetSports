import React from "react";
import { Box, Typography, Paper } from "@mui/material";
import Grid from "@mui/material/Grid";
import { Match } from "../../../../domain/entities/match";

interface LiveMatchStatsProps {
  match: Match;
}

export const LiveMatchStats: React.FC<LiveMatchStatsProps> = ({ match }) => {
  return (
    <Grid container spacing={2} sx={{ mb: 3 }}>
      {/* Possession Bar (Full Width) */}
      {(match.home_possession || match.away_possession) && (
        <Grid size={12}>
          <Paper sx={{ p: 2, bgcolor: "rgba(0,0,0,0.2)" }}>
            <Box display="flex" justifyContent="space-between" mb={1}>
              <Typography variant="caption" color="text.secondary">
                {match.home_possession ?? "0%"}
              </Typography>
              <Typography variant="caption" fontWeight="bold">
                Posesión
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {match.away_possession ?? "0%"}
              </Typography>
            </Box>
            <Box
              sx={{
                display: "flex",
                height: 8,
                borderRadius: 4,
                overflow: "hidden",
              }}
            >
              <Box
                sx={{
                  width: match.home_possession || "50%",
                  bgcolor: "primary.main",
                }}
              />
              <Box
                sx={{
                  width: match.away_possession || "50%",
                  bgcolor: "error.main",
                }}
              />
            </Box>
          </Paper>
        </Grid>
      )}

      {/* Stats Rows */}
      <Grid size={12}>
        <Paper sx={{ p: 2, bgcolor: "rgba(0,0,0,0.2)" }}>
          {/* Shots */}
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            mb={1.5}
            sx={{ borderBottom: "1px solid rgba(255,255,255,0.05)", pb: 1 }}
          >
            <Typography variant="body2" fontWeight="bold">
              {match.home_total_shots ?? 0} ({match.home_shots_on_target ?? 0})
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Tiros (Al Arco)
            </Typography>
            <Typography variant="body2" fontWeight="bold">
              {match.away_total_shots ?? 0} ({match.away_shots_on_target ?? 0})
            </Typography>
          </Box>

          {/* Corners */}
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            mb={1.5}
            sx={{ borderBottom: "1px solid rgba(255,255,255,0.05)", pb: 1 }}
          >
            <Typography variant="body2" fontWeight="bold" color="info.main">
              {match.home_corners ?? 0}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Córners
            </Typography>
            <Typography variant="body2" fontWeight="bold" color="info.main">
              {match.away_corners ?? 0}
            </Typography>
          </Box>

          {/* Yellow Cards */}
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            mb={1.5}
            sx={{ borderBottom: "1px solid rgba(255,255,255,0.05)", pb: 1 }}
          >
            <Typography
              variant="body2"
              fontWeight="bold"
              sx={{ color: "#facc15" }}
            >
              {match.home_yellow_cards ?? 0}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Tarjetas Amarillas
            </Typography>
            <Typography
              variant="body2"
              fontWeight="bold"
              sx={{ color: "#facc15" }}
            >
              {match.away_yellow_cards ?? 0}
            </Typography>
          </Box>

          {/* Red Cards */}
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            mb={1.5}
            sx={{ borderBottom: "1px solid rgba(255,255,255,0.05)", pb: 1 }}
          >
            <Typography
              variant="body2"
              fontWeight="bold"
              sx={{ color: "#ef4444" }}
            >
              {match.home_red_cards ?? 0}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Tarjetas Rojas
            </Typography>
            <Typography
              variant="body2"
              fontWeight="bold"
              sx={{ color: "#ef4444" }}
            >
              {match.away_red_cards ?? 0}
            </Typography>
          </Box>

          {/* Fouls / Offsides */}
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
          >
            <Box textAlign="left">
              <Typography
                variant="caption"
                display="block"
                color="text.secondary"
                sx={{ fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
              >
                Faltas: {match.home_fouls ?? 0}
              </Typography>
              <Typography
                variant="caption"
                display="block"
                color="text.secondary"
                sx={{ fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
              >
                Offsides: {match.home_offsides ?? 0}
              </Typography>
            </Box>
            <Typography variant="caption" color="text.secondary">
              Disciplina
            </Typography>
            <Box textAlign="right">
              <Typography
                variant="caption"
                display="block"
                color="text.secondary"
                sx={{ fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
              >
                Faltas: {match.away_fouls ?? 0}
              </Typography>
              <Typography
                variant="caption"
                display="block"
                color="text.secondary"
                sx={{ fontSize: { xs: "0.7rem", sm: "0.75rem" } }}
              >
                Offsides: {match.away_offsides ?? 0}
              </Typography>
            </Box>
          </Box>
        </Paper>
      </Grid>
    </Grid>
  );
};

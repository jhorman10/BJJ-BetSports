import { Box, Typography, Paper, styled } from "@mui/material";
import Grid from "@mui/material/Grid";
import { Flag, QueryStats } from "@mui/icons-material";

import { Match } from "../../../../domain/entities/match";

// --- Estilos Compartidos con LiveMatchCard ---
const CardBadge = styled(Box)<{ color: string }>(({ color }) => ({
  width: 10,
  height: 14,
  backgroundColor: color,
  borderRadius: 2,
  boxShadow: "0 1px 2px rgba(0,0,0,0.3)",
}));

interface LiveMatchStatsProps {
  match: Match;
}

export const LiveMatchStats: React.FC<LiveMatchStatsProps> = ({ match }) => {
  const hasShotsOnTarget =
    (match.home_shots_on_target ?? 0) > 0 ||
    (match.away_shots_on_target ?? 0) > 0;

  return (
    <Grid container spacing={2} sx={{ mb: 3 }}>
      {/* Possession Bar (Classic) */}
      {(match.home_possession || match.away_possession) && (
        <Grid size={12}>
          <Paper sx={{ p: { xs: 1.5, sm: 2 }, bgcolor: "rgba(0,0,0,0.2)", borderRadius: 2, overflow: "hidden" }}>
            <Box display="flex" justifyContent="space-between" mb={1} gap={1}>
              <Typography variant="body2" fontWeight="bold" sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.8rem", sm: "0.875rem" } }}>
                {match.home_possession ?? "50%"}
              </Typography>
              <Typography variant="caption" color="rgba(255,255,255,0.6)" sx={{ flexShrink: 0, fontSize: { xs: "0.6rem", sm: "0.75rem" } }}>
                Posesión
              </Typography>
              <Typography variant="body2" fontWeight="bold" sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.8rem", sm: "0.875rem" } }}>
                {match.away_possession ?? "50%"}
              </Typography>
            </Box>
            <Box
              sx={{
                display: "flex",
                height: 6,
                borderRadius: 3,
                overflow: "hidden",
                bgcolor: "rgba(255,255,255,0.05)",
              }}
            >
              <Box
                sx={{
                  width: match.home_possession || "50%",
                  bgcolor: "primary.main",
                  transition: "width 1s ease",
                }}
              />
              <Box
                sx={{
                  width: match.away_possession || "50%",
                  bgcolor: "error.main",
                  transition: "width 1s ease",
                }}
              />
            </Box>
          </Paper>
        </Grid>
      )}

      {/* Main Stats (Shots, Corners, Cards) */}
      <Grid size={12}>
        <Paper sx={{ p: { xs: 1.5, sm: 2 }, bgcolor: "rgba(0,0,0,0.2)", borderRadius: 2, overflow: "hidden" }}>
          {/* Shots on Target & Total */}
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            mb={1.5}
            gap={0.5}
            sx={{ borderBottom: "1px solid rgba(255,255,255,0.05)", pb: 1 }}
          >
            <Typography variant="body2" fontWeight="bold" sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.8rem", sm: "0.875rem" } }}>
              {match.home_total_shots ?? 0}
              {hasShotsOnTarget && ` (${match.home_shots_on_target ?? 0})`}
            </Typography>
            <Box display="flex" alignItems="center" gap={0.5} sx={{ flexShrink: 0 }}>
              <QueryStats
                sx={{ fontSize: { xs: 14, sm: 16 }, color: "primary.main", opacity: 0.8 }}
              />
              <Typography variant="caption" color="rgba(255,255,255,0.6)" sx={{ fontSize: { xs: "0.6rem", sm: "0.75rem" }, whiteSpace: "nowrap" }}>
                {hasShotsOnTarget ? "Tiros (Al Arco)" : "Tiros"}
              </Typography>
            </Box>
            <Typography variant="body2" fontWeight="bold" sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.8rem", sm: "0.875rem" } }}>
              {match.away_total_shots ?? 0}
              {hasShotsOnTarget && ` (${match.away_shots_on_target ?? 0})`}
            </Typography>
          </Box>

          {/* Corners */}
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            mb={1.5}
            gap={0.5}
            sx={{ borderBottom: "1px solid rgba(255,255,255,0.05)", pb: 1 }}
          >
            <Typography variant="body2" fontWeight="bold" sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.8rem", sm: "0.875rem" } }}>
              {match.home_corners ?? 0}
            </Typography>
            <Box display="flex" alignItems="center" gap={0.5} sx={{ flexShrink: 0 }}>
              <Flag sx={{ fontSize: { xs: 14, sm: 16 }, color: "#fbbf24", opacity: 0.8 }} />
              <Typography variant="caption" color="rgba(255,255,255,0.6)" sx={{ fontSize: { xs: "0.6rem", sm: "0.75rem" } }}>
                Córners
              </Typography>
            </Box>
            <Typography variant="body2" fontWeight="bold" sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.8rem", sm: "0.875rem" } }}>
              {match.away_corners ?? 0}
            </Typography>
          </Box>

          {/* Yellow Cards */}
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            mb={1.5}
            gap={0.5}
            sx={{ borderBottom: "1px solid rgba(255,255,255,0.05)", pb: 1 }}
          >
            <Typography variant="body2" fontWeight="bold" sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.8rem", sm: "0.875rem" } }}>
              {match.home_yellow_cards ?? 0}
            </Typography>
            <Box display="flex" alignItems="center" gap={0.5} sx={{ flexShrink: 0 }}>
              <CardBadge color="#facc15" />
              <Typography variant="caption" color="rgba(255,255,255,0.6)" sx={{ fontSize: { xs: "0.6rem", sm: "0.75rem" } }}>
                T. Amarillas
              </Typography>
            </Box>
            <Typography variant="body2" fontWeight="bold" sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.8rem", sm: "0.875rem" } }}>
              {match.away_yellow_cards ?? 0}
            </Typography>
          </Box>

          {/* Red Cards */}
          <Box
            display="flex"
            justifyContent="space-between"
            alignItems="center"
            mb={1.5}
            gap={0.5}
            sx={{ borderBottom: "1px solid rgba(255,255,255,0.05)", pb: 1 }}
          >
            <Typography variant="body2" fontWeight="bold" sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.8rem", sm: "0.875rem" } }}>
              {match.home_red_cards ?? 0}
            </Typography>
            <Box display="flex" alignItems="center" gap={0.5} sx={{ flexShrink: 0 }}>
              <CardBadge color="#ef4444" />
              <Typography variant="caption" color="rgba(255,255,255,0.6)" sx={{ fontSize: { xs: "0.6rem", sm: "0.75rem" } }}>
                T. Rojas
              </Typography>
            </Box>
            <Typography variant="body2" fontWeight="bold" sx={{ minWidth: 0, flexShrink: 1, fontSize: { xs: "0.8rem", sm: "0.875rem" } }}>
              {match.away_red_cards ?? 0}
            </Typography>
          </Box>

          {/* Fouls & Offsides — Section Header */}
          <Box mt={1.5} mb={1}>
            <Typography
              variant="caption"
              fontWeight={700}
              color="rgba(255,255,255,0.5)"
              sx={{
                textTransform: "uppercase",
                letterSpacing: "1px",
                fontSize: "0.6rem",
                display: "block",
                textAlign: "center",
                borderBottom: "1px solid rgba(255,255,255,0.05)",
                pb: 0.5,
              }}
            >
              Disciplina
            </Typography>
          </Box>
          <Box display="flex" justifyContent="space-between">
            <Box textAlign="left">
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
              >
                Faltas: <b>{match.home_fouls ?? 0}</b>
              </Typography>
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
              >
                Offsides: <b>{match.home_offsides ?? 0}</b>
              </Typography>
            </Box>
            <Box textAlign="right">
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
              >
                Faltas: <b>{match.away_fouls ?? 0}</b>
              </Typography>
              <Typography
                variant="caption"
                color="text.secondary"
                display="block"
              >
                Offsides: <b>{match.away_offsides ?? 0}</b>
              </Typography>
            </Box>
          </Box>
        </Paper>
      </Grid>
    </Grid>
  );
};

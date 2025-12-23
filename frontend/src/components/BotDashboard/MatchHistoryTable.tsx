import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  Typography,
  Box,
} from "@mui/material";
import { CheckCircle, Cancel } from "@mui/icons-material";

interface MatchPredictionHistory {
  match_id: string;
  home_team: string;
  away_team: string;
  match_date: string;
  predicted_winner: string;
  actual_winner: string;
  predicted_home_goals: number;
  predicted_away_goals: number;
  actual_home_goals: number;
  actual_away_goals: number;
  was_correct: boolean;
  confidence: number;
}

interface MatchHistoryTableProps {
  matches: MatchPredictionHistory[];
}

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "short",
  });
};

const getWinnerLabel = (
  winner: string,
  homeTeam: string,
  awayTeam: string
): string => {
  if (winner === "home") return homeTeam;
  if (winner === "away") return awayTeam;
  return "Empate";
};

const MatchHistoryTable: React.FC<MatchHistoryTableProps> = ({ matches }) => {
  if (!matches || matches.length === 0) {
    return (
      <Box p={3} textAlign="center">
        <Typography color="text.secondary">
          No hay histórico de predicciones disponible
        </Typography>
      </Box>
    );
  }

  return (
    <TableContainer
      component={Paper}
      sx={{
        bgcolor: "rgba(30, 41, 59, 0.6)",
        backdropFilter: "blur(10px)",
        border: "1px solid rgba(148, 163, 184, 0.1)",
      }}
    >
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell sx={{ color: "text.secondary", fontWeight: 600 }}>
              Fecha
            </TableCell>
            <TableCell sx={{ color: "text.secondary", fontWeight: 600 }}>
              Partido
            </TableCell>
            <TableCell
              align="center"
              sx={{ color: "text.secondary", fontWeight: 600 }}
            >
              Resultado
            </TableCell>
            <TableCell sx={{ color: "text.secondary", fontWeight: 600 }}>
              Predicción
            </TableCell>
            <TableCell
              align="center"
              sx={{ color: "text.secondary", fontWeight: 600 }}
            >
              Estado
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {matches.map((match) => (
            <TableRow
              key={match.match_id}
              sx={{
                "&:hover": {
                  bgcolor: "rgba(148, 163, 184, 0.05)",
                },
              }}
            >
              <TableCell sx={{ color: "white" }}>
                {formatDate(match.match_date)}
              </TableCell>
              <TableCell sx={{ color: "white" }}>
                <Typography variant="body2" fontWeight={500}>
                  {match.home_team} vs {match.away_team}
                </Typography>
              </TableCell>
              <TableCell align="center">
                <Typography
                  variant="body2"
                  fontWeight={700}
                  sx={{ color: "#10b981" }}
                >
                  {match.actual_home_goals} - {match.actual_away_goals}
                </Typography>
              </TableCell>
              <TableCell>
                <Typography variant="body2" color="text.secondary">
                  {getWinnerLabel(
                    match.predicted_winner,
                    match.home_team,
                    match.away_team
                  )}
                </Typography>
                <Typography variant="caption" color="text.disabled">
                  ({match.predicted_home_goals.toFixed(1)} -{" "}
                  {match.predicted_away_goals.toFixed(1)})
                </Typography>
              </TableCell>
              <TableCell align="center">
                {match.was_correct ? (
                  <Chip
                    icon={<CheckCircle />}
                    label="Acertada"
                    color="success"
                    size="small"
                    sx={{
                      bgcolor: "rgba(34, 197, 94, 0.2)",
                      color: "#10b981",
                      fontWeight: 600,
                    }}
                  />
                ) : (
                  <Chip
                    icon={<Cancel />}
                    label="Errada"
                    color="error"
                    size="small"
                    sx={{
                      bgcolor: "rgba(239, 68, 68, 0.2)",
                      color: "#ef4444",
                      fontWeight: 600,
                    }}
                  />
                )}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export default MatchHistoryTable;

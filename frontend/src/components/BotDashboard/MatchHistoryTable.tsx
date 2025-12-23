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
  Card,
  CardContent,
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
  suggested_pick?: string | null;
  pick_was_correct?: boolean | null;
  expected_value?: number | null;
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
    <>
      {/* Desktop Table View */}
      <Box sx={{ display: { xs: "none", md: "block" } }}>
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
                <TableCell sx={{ color: "text.secondary", fontWeight: 600 }}>
                  Pick Sugerido
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
                  <TableCell>
                    {match.suggested_pick ? (
                      <Box>
                        <Typography
                          variant="body2"
                          fontWeight={600}
                          color="#fbbf24"
                        >
                          {match.suggested_pick}
                        </Typography>
                        {match.expected_value && (
                          <Typography variant="caption" color="text.disabled">
                            EV: +{match.expected_value.toFixed(1)}%
                          </Typography>
                        )}
                      </Box>
                    ) : (
                      <Typography variant="caption" color="text.disabled">
                        No pick
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell align="center">
                    {match.suggested_pick ? (
                      // Show pick status if there was a value bet
                      match.pick_was_correct ? (
                        <Chip
                          icon={<CheckCircle />}
                          label="Pick Ganador"
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
                          label="Pick Perdedor"
                          color="error"
                          size="small"
                          sx={{
                            bgcolor: "rgba(239, 68, 68, 0.2)",
                            color: "#ef4444",
                            fontWeight: 600,
                          }}
                        />
                      )
                    ) : // Show prediction status if no value bet
                    match.was_correct ? (
                      <Chip
                        icon={<CheckCircle />}
                        label="Acertada"
                        color="success"
                        size="small"
                        variant="outlined"
                        sx={{
                          borderColor: "rgba(34, 197, 94, 0.3)",
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
                        variant="outlined"
                        sx={{
                          borderColor: "rgba(239, 68, 68, 0.3)",
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
      </Box>

      <Box sx={{ display: { xs: "block", md: "none" } }}>
        {matches.map((match) => (
          <Card
            key={match.match_id}
            sx={{
              mb: 2,
              position: "relative",
              bgcolor: "rgba(30, 41, 59, 0.6)",
              backdropFilter: "blur(10px)",
              border: "1px solid rgba(148, 163, 184, 0.1)",
            }}
          >
            {/* Status Chip and Date positioned top‑right */}
            <Box
              sx={{
                position: "absolute",
                top: 8,
                right: 8,
                zIndex: 10,
                display: "flex",
                flexDirection: "column",
                alignItems: "flex-end",
                gap: "5px",
              }}
            >
              {match.suggested_pick ? (
                match.pick_was_correct ? (
                  <Chip
                    icon={<CheckCircle />}
                    label="Pick Ganador"
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
                    label="Pick Perdedor"
                    color="error"
                    size="small"
                    sx={{
                      bgcolor: "rgba(239, 68, 68, 0.2)",
                      color: "#ef4444",
                      fontWeight: 600,
                    }}
                  />
                )
              ) : match.was_correct ? (
                <Chip
                  icon={<CheckCircle />}
                  label="Acertada"
                  color="success"
                  size="small"
                  variant="outlined"
                  sx={{
                    borderColor: "rgba(34, 197, 94, 0.3)",
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
                  variant="outlined"
                  sx={{
                    borderColor: "rgba(239, 68, 68, 0.3)",
                    color: "#ef4444",
                    fontWeight: 600,
                  }}
                />
              )}
              {/* Date below chip */}
              <Typography variant="caption" color="text.secondary">
                {formatDate(match.match_date)}
              </Typography>
            </Box>
            <CardContent>
              {/* Score */}
              <Typography variant="h6" fontWeight={700} color="#10b981" mb={1}>
                {match.actual_home_goals} - {match.actual_away_goals}
              </Typography>

              {/* Prediction */}
              <Box mb={1}>
                <Typography variant="caption" color="text.disabled">
                  Predicción:
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {getWinnerLabel(
                    match.predicted_winner,
                    match.home_team,
                    match.away_team
                  )}{" "}
                  ({match.predicted_home_goals.toFixed(1)} -{" "}
                  {match.predicted_away_goals.toFixed(1)})
                </Typography>
              </Box>

              {/* Suggested Pick */}
              {match.suggested_pick && (
                <Box mb={1}>
                  <Typography variant="caption" color="text.disabled">
                    Pick Sugerido:
                  </Typography>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography
                      variant="body2"
                      fontWeight={600}
                      color="#fbbf24"
                    >
                      {match.suggested_pick}
                    </Typography>
                    {match.expected_value && (
                      <Typography variant="caption" color="text.disabled">
                        EV: +{match.expected_value.toFixed(1)}%
                      </Typography>
                    )}
                  </Box>
                </Box>
              )}
            </CardContent>
          </Card>
        ))}
      </Box>
    </>
  );
};

export default MatchHistoryTable;

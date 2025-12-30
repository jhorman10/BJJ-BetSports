import React, { useState } from "react";
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
  TableSortLabel,
  Collapse,
  IconButton,
  TablePagination,
  TextField,
  InputAdornment,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import {
  CheckCircle,
  Cancel,
  KeyboardArrowDown,
  Search,
} from "@mui/icons-material";
import { MatchHistoryTableProps } from "../../../types";
import {
  getPickColor,
  getMarketIcon,
  getUniquePicks,
} from "../../../utils/marketUtils";

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString("es-ES", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
};

const getPredictionLabel = (
  winner: string,
  homeTeam: string,
  awayTeam: string
): string => {
  // More descriptive prediction labels
  if (winner === "1" || winner === "home") return `${homeTeam} gana`;
  if (winner === "2" || winner === "away") return `${awayTeam} gana`;
  if (winner === "X" || winner === "draw") return "Empate";
  return "Empate";
};

// Map market types to readable Spanish labels
const MARKET_TYPE_LABELS: Record<string, string> = {
  winner: "Resultado 1X2",
  draw: "Empate",
  double_chance_1x: "Doble Oportunidad 1X",
  double_chance_x2: "Doble Oportunidad X2",
  double_chance_12: "Doble Oportunidad 12",
  va_handicap: "Hándicap Asiático",
  goals_over: "Más de 4.5 Goles",
  goals_under: "Menos de 4.5 Goles",
  goals_over_0_5: "Más de 0.5 Goles",
  goals_over_1_5: "Más de 1.5 Goles",
  goals_over_2_5: "Más de 2.5 Goles",
  goals_over_3_5: "Más de 3.5 Goles",
  goals_under_0_5: "Menos de 0.5 Goles",
  goals_under_1_5: "Menos de 1.5 Goles",
  goals_under_2_5: "Menos de 2.5 Goles",
  goals_under_3_5: "Menos de 3.5 Goles",
  team_goals_over: "Goles por Equipo +0.5",
  team_goals_under: "Goles por Equipo -0.5",
  btts_yes: "Ambos Marcan (Sí)",
  btts_no: "Ambos Marcan (No)",
  corners_over: "Córners Totales +9.5",
  corners_under: "Córners Totales -9.5",
  home_corners_over: "Córners Local +4.5",
  home_corners_under: "Córners Local -4.5",
  away_corners_over: "Córners Visitante +4.5",
  away_corners_under: "Córners Visitante -4.5",
  cards_over: "Tarjetas Totales +4.5",
  cards_under: "Tarjetas Totales -4.5",
  home_cards_over: "Tarjetas Local +1.5",
  home_cards_under: "Tarjetas Local -1.5",
  away_cards_over: "Tarjetas Visitante +1.5",
  away_cards_under: "Tarjetas Visitante -1.5",
  red_cards: "Tarjeta Roja en el Partido",
};

const getMarketLabel = (marketType: string | undefined): string => {
  if (!marketType) return "Desconocido";
  return MARKET_TYPE_LABELS[marketType] || marketType.replace(/_/g, " ");
};

// Utility functions getPickColor, getMarketIcon, getUniquePicks imported from marketUtils

const MatchHistoryTable: React.FC<MatchHistoryTableProps> = ({ matches }) => {
  type SortColumn = "date" | "result" | "default";
  type SortDirection = "asc" | "desc";

  const [sortColumn, setSortColumn] = useState<SortColumn>("default");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [searchQuery, setSearchQuery] = useState("");

  if (!matches || matches.length === 0) {
    return (
      <Box p={3} textAlign="center">
        <Typography color="text.secondary">
          No hay histórico de predicciones disponible
        </Typography>
      </Box>
    );
  }

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      // Toggle direction if same column
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      // New column, default to descending
      setSortColumn(column);
      setSortDirection("desc");
    }
  };

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const filteredMatches = React.useMemo(() => {
    if (!searchQuery) return matches;
    const lowerQuery = searchQuery.toLowerCase();
    return matches.filter(
      (match) =>
        match.home_team.toLowerCase().includes(lowerQuery) ||
        match.away_team.toLowerCase().includes(lowerQuery)
    );
  }, [matches, searchQuery]);

  const sortedMatches = React.useMemo(() => {
    const sorted = [...filteredMatches];

    // Helper to get timestamp
    const getTime = (m: any) => new Date(m.match_date).getTime();

    if (sortColumn === "date") {
      sorted.sort((a, b) => {
        const timeA = getTime(a);
        const timeB = getTime(b);
        return sortDirection === "asc" ? timeA - timeB : timeB - timeA;
      });
    } else if (sortColumn === "result") {
      sorted.sort((a, b) => {
        // Get correctness value (1 for correct, 0 for incorrect)
        // This matches "what is painted" (Green vs Red chips)
        const getCorrectness = (m: any) => {
          return m.was_correct ? 1 : 0;
        };

        const valA = getCorrectness(a);
        const valB = getCorrectness(b);

        if (valA !== valB) {
          return sortDirection === "asc" ? valA - valB : valB - valA;
        }

        // Tie-breaker: Always sort by Date Descending (Most recent first)
        return getTime(b) - getTime(a);
      });
    } else {
      // Default sorting: Date Descending (Most recent first)
      sorted.sort((a, b) => getTime(b) - getTime(a));
    }

    return sorted;
  }, [filteredMatches, sortColumn, sortDirection]);

  const paginatedMatches = sortedMatches.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  return (
    <>
      <Box mb={3}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Buscar equipo..."
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setPage(0);
          }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search sx={{ color: "text.secondary" }} />
              </InputAdornment>
            ),
          }}
          size="small"
          sx={{
            bgcolor: "rgba(30, 41, 59, 0.6)",
            "& .MuiOutlinedInput-root": {
              "& fieldset": { borderColor: "rgba(148, 163, 184, 0.3)" },
              "&:hover fieldset": { borderColor: "rgba(148, 163, 184, 0.5)" },
              "&.Mui-focused fieldset": { borderColor: "#6366f1" },
            },
            input: { color: "white" },
          }}
        />
      </Box>

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
                <TableCell sx={{ width: 48 }} />
                {/* Expand button column */}
                <TableCell sx={{ color: "text.secondary", fontWeight: 600 }}>
                  <TableSortLabel
                    active={sortColumn === "date"}
                    direction={sortColumn === "date" ? sortDirection : "desc"}
                    onClick={() => handleSort("date")}
                    sx={{
                      color: "rgba(255,255,255,0.7) !important",
                      "&.Mui-active": {
                        color: "#6366f1 !important",
                      },
                      "& .MuiTableSortLabel-icon": {
                        color: "#6366f1 !important",
                      },
                    }}
                  >
                    Fecha
                  </TableSortLabel>
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
                  <TableSortLabel
                    active={sortColumn === "result"}
                    direction={sortColumn === "result" ? sortDirection : "desc"}
                    onClick={() => handleSort("result")}
                    sx={{
                      color: "rgba(255,255,255,0.7) !important",
                      "&.Mui-active": {
                        color: "#6366f1 !important",
                      },
                      "& .MuiTableSortLabel-icon": {
                        color: "#6366f1 !important",
                      },
                    }}
                  >
                    Estado
                  </TableSortLabel>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {paginatedMatches.map((match) => (
                <React.Fragment key={match.match_id}>
                  <TableRow
                    sx={{
                      "&:hover": {
                        bgcolor: "rgba(148, 163, 184, 0.05)",
                        cursor: match.picks?.length > 0 ? "pointer" : "default",
                      },
                      "& td, & th": {
                        borderBottom:
                          expandedRow === match.match_id ? "none" : undefined,
                      },
                    }}
                    onClick={() => {
                      if (match.picks?.length > 0) {
                        setExpandedRow(
                          expandedRow === match.match_id ? null : match.match_id
                        );
                      }
                    }}
                  >
                    <TableCell sx={{ width: 48, p: 1 }}>
                      {match.picks?.length > 0 && (
                        <IconButton
                          size="small"
                          sx={{
                            color: "#6366f1",
                            transition: "transform 0.3s ease",
                            transform:
                              expandedRow === match.match_id
                                ? "rotate(180deg)"
                                : "rotate(0deg)",
                          }}
                        >
                          <KeyboardArrowDown />
                        </IconButton>
                      )}
                    </TableCell>

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
                      <Typography
                        variant="body2"
                        fontWeight={600}
                        color="rgba(255,255,255,0.9)"
                      >
                        {getPredictionLabel(
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
                          label="Predicción Correcta"
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
                          label="Predicción Errada"
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

                  {match.picks?.length > 0 && (
                    <TableRow>
                      <TableCell colSpan={7} sx={{ p: 0, border: 0 }}>
                        <Collapse
                          in={expandedRow === match.match_id}
                          timeout="auto"
                          unmountOnExit
                        >
                          <Box
                            sx={{
                              p: 3,
                              bgcolor: "rgba(15, 23, 42, 0.6)",
                            }}
                          >
                            <Box
                              display="flex"
                              alignItems="center"
                              justifyContent="space-between"
                              mb={2}
                            >
                              <Typography
                                variant="h6"
                                fontWeight={700}
                                color="white"
                              >
                                📊 Todos los Picks del Partido
                              </Typography>

                              {(() => {
                                const uniquePicks = getUniquePicks(
                                  match.picks || []
                                );
                                const correctCount = uniquePicks.filter(
                                  (p) => p.was_correct
                                ).length;
                                const wrongCount = uniquePicks.filter(
                                  (p) => !p.was_correct
                                ).length;

                                return (
                                  <Box display="flex" gap={1}>
                                    <Chip
                                      icon={
                                        <CheckCircle
                                          sx={{ fontSize: "16px !important" }}
                                        />
                                      }
                                      label={`${correctCount} Aciertos`}
                                      size="small"
                                      sx={{
                                        bgcolor: "rgba(16, 185, 129, 0.1)",
                                        color: "#10b981",
                                        border:
                                          "1px solid rgba(16, 185, 129, 0.2)",
                                        fontWeight: 600,
                                        height: 24,
                                      }}
                                    />
                                    <Chip
                                      icon={
                                        <Cancel
                                          sx={{ fontSize: "16px !important" }}
                                        />
                                      }
                                      label={`${wrongCount} Fallos`}
                                      size="small"
                                      sx={{
                                        bgcolor: "rgba(239, 68, 68, 0.1)",
                                        color: "#ef4444",
                                        border:
                                          "1px solid rgba(239, 68, 68, 0.2)",
                                        fontWeight: 600,
                                        height: 24,
                                      }}
                                    />
                                  </Box>
                                );
                              })()}
                            </Box>
                            <Grid container spacing={2}>
                              {getUniquePicks(match.picks || [])
                                .sort(
                                  (a, b) =>
                                    (b.probability || b.confidence || 0) -
                                    (a.probability || a.confidence || 0)
                                )
                                .map((pick, index) => {
                                  const confColor = getPickColor(
                                    pick.probability || pick.confidence || 0
                                  );
                                  return (
                                    <Grid
                                      size={{ xs: 12, sm: 6, md: 4 }}
                                      key={index}
                                    >
                                      <Card
                                        sx={{
                                          background: pick.was_correct
                                            ? "linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.1) 100%)"
                                            : "linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.1) 100%)",
                                          border: `1px solid ${
                                            pick.was_correct
                                              ? "rgba(16, 185, 129, 0.3)"
                                              : "rgba(239, 68, 68, 0.3)"
                                          }`,
                                          borderRadius: 2,
                                        }}
                                      >
                                        <CardContent sx={{ p: 2 }}>
                                          <Box
                                            display="flex"
                                            justifyContent="space-between"
                                            alignItems="flex-start"
                                            mb={1}
                                          >
                                            <Typography
                                              variant="caption"
                                              color="text.secondary"
                                              fontWeight={600}
                                              textTransform="uppercase"
                                              sx={{
                                                display: "flex",
                                                alignItems: "center",
                                                gap: 0.5,
                                              }}
                                            >
                                              <span
                                                style={{ fontSize: "1.2em" }}
                                              >
                                                {getMarketIcon(
                                                  pick.market_type
                                                )}
                                              </span>{" "}
                                              {pick.market_label ||
                                                getMarketLabel(
                                                  pick.market_type
                                                )}
                                              {pick.is_contrarian && (
                                                <Chip
                                                  label="VALUE BET"
                                                  size="small"
                                                  sx={{
                                                    bgcolor:
                                                      "rgba(139, 92, 246, 0.2)",
                                                    color: "#8b5cf6",
                                                    fontSize: "0.65rem",
                                                    height: 20,
                                                    fontWeight: 700,
                                                    border:
                                                      "1px solid rgba(139, 92, 246, 0.3)",
                                                  }}
                                                />
                                              )}
                                            </Typography>
                                            {pick.was_correct ? (
                                              <CheckCircle
                                                sx={{
                                                  fontSize: 20,
                                                  color: "#10b981",
                                                }}
                                              />
                                            ) : (
                                              <Cancel
                                                sx={{
                                                  fontSize: 20,
                                                  color: "#ef4444",
                                                }}
                                              />
                                            )}
                                          </Box>
                                          <Box
                                            display="flex"
                                            gap={1}
                                            flexWrap="wrap"
                                          >
                                            {pick.expected_value !==
                                              undefined &&
                                              pick.expected_value > 0 && (
                                                <Chip
                                                  label={`EV: +${pick.expected_value.toFixed(
                                                    1
                                                  )}%`}
                                                  size="small"
                                                  sx={{
                                                    bgcolor:
                                                      "rgba(251, 191, 36, 0.2)",
                                                    color: "#fbbf24",
                                                    fontSize: "0.65rem",
                                                    height: 20,
                                                  }}
                                                />
                                              )}
                                            <Chip
                                              label={`Conf: ${(
                                                (pick.probability ||
                                                  pick.confidence ||
                                                  0) * 100
                                              ).toFixed(0)}%`}
                                              size="small"
                                              sx={{
                                                bgcolor: `${confColor}20`,
                                                color: confColor,
                                                fontSize: "0.65rem",
                                                height: 20,
                                                fontWeight: 700,
                                              }}
                                            />
                                            {pick.suggested_stake !==
                                              undefined &&
                                              pick.suggested_stake > 0 && (
                                                <Chip
                                                  label={`Stake: ${pick.suggested_stake.toFixed(
                                                    2
                                                  )}u`}
                                                  size="small"
                                                  sx={{
                                                    bgcolor:
                                                      "rgba(56, 189, 248, 0.1)",
                                                    color: "#38bdf8",
                                                    fontSize: "0.65rem",
                                                    height: 20,
                                                    fontWeight: 600,
                                                    border:
                                                      "1px solid rgba(56, 189, 248, 0.2)",
                                                  }}
                                                />
                                              )}
                                            {pick.clv_beat !== undefined && (
                                              <Chip
                                                label={
                                                  pick.clv_beat
                                                    ? "CLV WIN"
                                                    : "CLV LOSS"
                                                }
                                                size="small"
                                                sx={{
                                                  bgcolor: pick.clv_beat
                                                    ? "rgba(16, 185, 129, 0.1)"
                                                    : "rgba(239, 68, 68, 0.1)",
                                                  color: pick.clv_beat
                                                    ? "#10b981"
                                                    : "#ef4444",
                                                  fontSize: "0.65rem",
                                                  height: 20,
                                                  fontWeight: 600,
                                                  borderColor: pick.clv_beat
                                                    ? "rgba(16, 185, 129, 0.2)"
                                                    : "rgba(239, 68, 68, 0.2)",
                                                  borderWidth: 1,
                                                  borderStyle: "solid",
                                                }}
                                              />
                                            )}
                                          </Box>
                                        </CardContent>
                                      </Card>
                                    </Grid>
                                  );
                                })}
                            </Grid>
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[10, 25, 50, 100]}
          component="div"
          count={sortedMatches.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          labelRowsPerPage="Filas por página:"
          sx={{
            color: "white",
            ".MuiTablePagination-selectLabel, .MuiTablePagination-displayedRows":
              {
                color: "rgba(255, 255, 255, 0.7)",
              },
            ".MuiTablePagination-select, .MuiTablePagination-actions": {
              color: "white",
            },
          }}
        />
      </Box>

      {/* Mobile Card View */}
      <Box sx={{ display: { xs: "block", md: "none" } }}>
        {paginatedMatches.map((match) => (
          <Card
            key={match.match_id}
            sx={{
              mb: 2,
              position: "relative",
              background:
                "linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)",
              backdropFilter: "blur(20px)",
              border: "1px solid rgba(148, 163, 184, 0.2)",
              borderRadius: 2,
            }}
          >
            <CardContent sx={{ p: 2.5 }}>
              {/* Header: Fecha y Estado */}
              <Box
                display="flex"
                justifyContent="space-between"
                alignItems="flex-start"
                mb={2}
              >
                <Typography
                  variant="caption"
                  color="text.secondary"
                  fontWeight={600}
                >
                  {formatDate(match.match_date)}
                </Typography>

                {/* Estado - mismo que desktop */}
                {/* Estado - mismo que desktop */}
                {match.was_correct ? (
                  <Chip
                    icon={<CheckCircle />}
                    label="Predicción Correcta"
                    color="success"
                    size="small"
                    variant="outlined"
                    sx={{
                      borderColor: "rgba(34, 197, 94, 0.3)",
                      color: "#10b981",
                      fontWeight: 600,
                      fontSize: "0.7rem",
                    }}
                  />
                ) : (
                  <Chip
                    icon={<Cancel />}
                    label="Predicción Errada"
                    color="error"
                    size="small"
                    variant="outlined"
                    sx={{
                      borderColor: "rgba(239, 68, 68, 0.3)",
                      color: "#ef4444",
                      fontWeight: 600,
                      fontSize: "0.7rem",
                    }}
                  />
                )}
              </Box>

              {/* Partido y Resultado */}
              <Box mb={1.5}>
                <Typography
                  variant="body2"
                  fontWeight={600}
                  color="white"
                  mb={0.5}
                >
                  {match.home_team} vs {match.away_team}
                </Typography>
                <Typography
                  variant="body2"
                  fontWeight={700}
                  sx={{ color: "#10b981" }}
                >
                  Resultado: {match.actual_home_goals} -{" "}
                  {match.actual_away_goals}
                </Typography>
              </Box>

              {/* Predicción */}
              <Box mb={1.5}>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  display="block"
                  mb={0.5}
                >
                  Predicción del resultado:
                </Typography>
                <Typography
                  variant="body2"
                  fontWeight={600}
                  color="rgba(255,255,255,0.9)"
                >
                  {getPredictionLabel(
                    match.predicted_winner,
                    match.home_team,
                    match.away_team
                  )}{" "}
                  <Typography
                    component="span"
                    variant="caption"
                    color="text.disabled"
                  >
                    ({match.predicted_home_goals.toFixed(1)} -{" "}
                    {match.predicted_away_goals.toFixed(1)})
                  </Typography>
                </Typography>
              </Box>

              {/* Mobile: All Picks */}
              {match.picks?.length > 0 && (
                <Box mt={2}>
                  <Box
                    display="flex"
                    justifyContent="space-between"
                    alignItems="center"
                    mb={1}
                    onClick={() =>
                      setExpandedRow(
                        expandedRow === match.match_id ? null : match.match_id
                      )
                    }
                    sx={{ cursor: "pointer" }}
                  >
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      fontWeight={600}
                    >
                      📊 TODOS ({getUniquePicks(match.picks || []).length})
                    </Typography>

                    {(() => {
                      const uniquePicks = getUniquePicks(match.picks || []);
                      const correctCount = uniquePicks.filter(
                        (p) => p.was_correct
                      ).length;
                      const wrongCount = uniquePicks.filter(
                        (p) => !p.was_correct
                      ).length;

                      return (
                        <Box display="flex" gap={1} mr={1}>
                          <span
                            style={{
                              color: "#10b981",
                              fontSize: "0.75rem",
                              fontWeight: 600,
                            }}
                          >
                            ✓ {correctCount}
                          </span>
                          <span
                            style={{
                              color: "#ef4444",
                              fontSize: "0.75rem",
                              fontWeight: 600,
                            }}
                          >
                            ✗ {wrongCount}
                          </span>
                        </Box>
                      );
                    })()}

                    <IconButton
                      size="small"
                      sx={{
                        p: 0,
                        color: "#6366f1",
                        transition: "transform 0.3s ease",
                        transform:
                          expandedRow === match.match_id
                            ? "rotate(180deg)"
                            : "rotate(0deg)",
                      }}
                    >
                      <KeyboardArrowDown />
                    </IconButton>
                  </Box>
                  <Collapse
                    in={expandedRow === match.match_id}
                    timeout="auto"
                    unmountOnExit
                  >
                    {getUniquePicks(match.picks || [])
                      .sort(
                        (a, b) =>
                          (b.probability || b.confidence || 0) -
                          (a.probability || a.confidence || 0)
                      )
                      .map((pick, index) => {
                        const confColor = getPickColor(pick.confidence || 0);
                        return (
                          <Box
                            key={index}
                            sx={{
                              p: 2,
                              mb: 1.5,
                              borderRadius: 2,
                              background: pick.was_correct
                                ? "linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.1) 100%)"
                                : "linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.1) 100%)",
                              border: `1px solid ${
                                pick.was_correct
                                  ? "rgba(16, 185, 129, 0.3)"
                                  : "rgba(239, 68, 68, 0.3)"
                              }`,
                            }}
                          >
                            <Box
                              display="flex"
                              justifyContent="space-between"
                              alignItems="flex-start"
                              mb={1}
                            >
                              <Typography
                                variant="caption"
                                color="text.secondary"
                                fontWeight={600}
                                textTransform="uppercase"
                                sx={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: 0.5,
                                  flexWrap: "wrap",
                                  wordBreak: "break-word",
                                  overflowWrap: "break-word",
                                }}
                              >
                                <span
                                  style={{ fontSize: "1.2em", flexShrink: 0 }}
                                >
                                  {getMarketIcon(pick.market_type)}
                                </span>{" "}
                                <span style={{ wordBreak: "break-word" }}>
                                  {pick.market_label ||
                                    getMarketLabel(pick.market_type)}
                                </span>
                                {pick.is_contrarian && (
                                  <Chip
                                    label="VALUE BET"
                                    size="small"
                                    sx={{
                                      bgcolor: "rgba(139, 92, 246, 0.2)",
                                      color: "#8b5cf6",
                                      fontSize: "0.65rem",
                                      height: 20,
                                      fontWeight: 700,
                                      border:
                                        "1px solid rgba(139, 92, 246, 0.3)",
                                      flexShrink: 0,
                                    }}
                                  />
                                )}
                              </Typography>
                              {pick.was_correct ? (
                                <CheckCircle
                                  sx={{
                                    fontSize: 20,
                                    color: "#10b981",
                                  }}
                                />
                              ) : (
                                <Cancel
                                  sx={{
                                    fontSize: 20,
                                    color: "#ef4444",
                                  }}
                                />
                              )}
                            </Box>
                            <Box display="flex" gap={1} flexWrap="wrap">
                              {pick.expected_value !== undefined &&
                                pick.expected_value > 0 && (
                                  <Chip
                                    label={`EV: +${pick.expected_value.toFixed(
                                      1
                                    )}%`}
                                    size="small"
                                    sx={{
                                      bgcolor: "rgba(251, 191, 36, 0.2)",
                                      color: "#fbbf24",
                                      fontSize: "0.65rem",
                                      height: 20,
                                    }}
                                  />
                                )}
                              <Chip
                                label={`Conf: ${(
                                  (pick.probability || pick.confidence || 0) *
                                  100
                                ).toFixed(0)}%`}
                                size="small"
                                sx={{
                                  bgcolor: `${confColor}20`,
                                  color: confColor,
                                  fontSize: "0.65rem",
                                  height: 20,
                                  fontWeight: 700,
                                }}
                              />
                              {pick.suggested_stake !== undefined &&
                                pick.suggested_stake > 0 && (
                                  <Chip
                                    label={`Stake: ${pick.suggested_stake.toFixed(
                                      2
                                    )}u`}
                                    size="small"
                                    sx={{
                                      bgcolor: "rgba(56, 189, 248, 0.1)",
                                      color: "#38bdf8",
                                      fontSize: "0.65rem",
                                      height: 20,
                                      fontWeight: 600,
                                      border:
                                        "1px solid rgba(56, 189, 248, 0.2)",
                                    }}
                                  />
                                )}
                              {pick.clv_beat !== undefined && (
                                <Chip
                                  label={pick.clv_beat ? "CLV WIN" : "CLV LOSS"}
                                  size="small"
                                  sx={{
                                    bgcolor: pick.clv_beat
                                      ? "rgba(16, 185, 129, 0.1)"
                                      : "rgba(239, 68, 68, 0.1)",
                                    color: pick.clv_beat
                                      ? "#10b981"
                                      : "#ef4444",
                                    fontSize: "0.65rem",
                                    height: 20,
                                    fontWeight: 600,
                                    borderColor: pick.clv_beat
                                      ? "rgba(16, 185, 129, 0.2)"
                                      : "rgba(239, 68, 68, 0.2)",
                                    borderWidth: 1,
                                    borderStyle: "solid",
                                  }}
                                />
                              )}
                            </Box>
                          </Box>
                        );
                      })}
                  </Collapse>
                </Box>
              )}
            </CardContent>
          </Card>
        ))}
        {/* Pagination options synchronized with desktop */}
        <TablePagination
          rowsPerPageOptions={[10, 25, 50, 100]}
          component="div"
          count={sortedMatches.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          labelRowsPerPage="Filas:"
          sx={{
            color: "white",
            ".MuiTablePagination-selectLabel, .MuiTablePagination-displayedRows":
              {
                color: "rgba(255, 255, 255, 0.7)",
              },
            ".MuiTablePagination-select, .MuiTablePagination-actions": {
              color: "white",
            },
          }}
        />
      </Box>
    </>
  );
};

export default React.memo(MatchHistoryTable);

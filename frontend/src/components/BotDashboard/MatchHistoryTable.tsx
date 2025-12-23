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
  Grid,
  TablePagination,
  TextField,
  InputAdornment,
} from "@mui/material";
import {
  CheckCircle,
  Cancel,
  KeyboardArrowDown,
  Search,
} from "@mui/icons-material";
import { MatchHistoryTableProps } from "../../types";

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

const getPickColor = (probability: number): string => {
  if (probability > 0.7) return "#22c55e";
  if (probability > 0.5) return "#f59e0b";
  return "#ef4444";
};

const getUniquePicks = (picks: any[]) => {
  if (!picks) return [];
  const seen = new Set();
  const unique = picks.filter((pick) => {
    const key = `${pick.market_type}-${pick.market_label}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  return unique.sort((a, b) => (b.confidence || 0) - (a.confidence || 0));
};

const getMarketIcon = (marketType: string): string => {
  switch (marketType) {
    case "corners_over":
    case "corners_under":
    case "home_corners_over":
    case "away_corners_over":
      return "⚑";
    case "cards_over":
    case "cards_under":
    case "home_cards_over":
    case "away_cards_over":
      return "🟨";
    case "red_cards":
      return "🟥";
    case "va_handicap":
      return "⚖️";
    case "winner":
      return "🏆";
    case "double_chance":
      return "🛡️";
    case "draw":
      return "🤝";
    case "goals_over":
    case "goals_under":
      return "⚽";
    case "btts_yes":
    case "btts_no":
      return "🥅";
    default:
      return "📊";
  }
};

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
          if (m.suggested_pick) return m.pick_was_correct ? 1 : 0;
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
                            <Typography
                              variant="h6"
                              fontWeight={700}
                              color="white"
                              mb={2}
                            >
                              📊 Todos los Picks del Partido
                            </Typography>
                            <Grid container spacing={2}>
                              {getUniquePicks(match.picks).map(
                                (pick, index) => {
                                  const confColor = getPickColor(
                                    pick.confidence || 0
                                  );
                                  return (
                                    <Grid
                                      item
                                      xs={12}
                                      sm={6}
                                      md={4}
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
                                              {pick.market_type?.replace(
                                                /_/g,
                                                " "
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
                                          <Typography
                                            variant="body2"
                                            fontWeight={700}
                                            color={
                                              pick.was_correct
                                                ? "#10b981"
                                                : "#ef4444"
                                            }
                                            mb={1}
                                          >
                                            {pick.market_label}
                                          </Typography>
                                          <Box
                                            display="flex"
                                            gap={1}
                                            flexWrap="wrap"
                                          >
                                            {pick.expected_value !==
                                              undefined && (
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
                                                (pick.confidence ?? 0) * 100
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
                                          </Box>
                                        </CardContent>
                                      </Card>
                                    </Grid>
                                  );
                                }
                              )}
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
                      📊 TODOS LOS PICKS ({getUniquePicks(match.picks).length})
                    </Typography>
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
                    {getUniquePicks(match.picks).map((pick, index) => {
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
                              }}
                            >
                              <span style={{ fontSize: "1.2em" }}>
                                {getMarketIcon(pick.market_type)}
                              </span>{" "}
                              {pick.market_type?.replace(/_/g, " ")}
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
                                    border: "1px solid rgba(139, 92, 246, 0.3)",
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
                          <Typography
                            variant="body2"
                            fontWeight={700}
                            color={pick.was_correct ? "#10b981" : "#ef4444"}
                            mb={1}
                          >
                            {pick.market_label}
                          </Typography>
                          <Box display="flex" gap={1} flexWrap="wrap">
                            {pick.expected_value !== undefined && (
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
                                (pick.confidence ?? 0) * 100
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

export default MatchHistoryTable;

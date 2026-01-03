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
  TableSortLabel,
  Collapse,
  IconButton,
  TablePagination,
  TextField,
  InputAdornment,
  Tooltip,
} from "@mui/material";
import Grid from "@mui/material/Grid";
import {
  CheckCircle,
  Cancel,
  KeyboardArrowDown,
  Search,
  SmartToy,
} from "@mui/icons-material";
import {
  MatchHistoryTableProps,
  MatchPredictionHistory,
  SuggestedPick,
} from "../../../types";
import {
  getPickColor,
  getMarketIcon,
  getUniquePicks,
} from "../../../utils/marketUtils";
import { useMatchHistoryTable } from "../../hooks/useMatchHistoryTable";

// --- Utility Functions ---
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
  if (winner === "1" || winner === "home") return `${homeTeam} gana`;
  if (winner === "2" || winner === "away") return `${awayTeam} gana`;
  if (winner === "X" || winner === "draw") return "Empate";
  return "Empate";
};

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

// --- Sub-Components ---

const PickChip = ({
  icon,
  label,
  color,
  sx = {},
}: {
  icon?: React.ReactElement;
  label: string;
  color?:
    | "success"
    | "error"
    | "default"
    | "primary"
    | "secondary"
    | "info"
    | "warning";
  sx?: any;
}) => (
  <Chip
    icon={icon}
    label={label}
    color={color}
    size="small"
    variant="outlined"
    sx={{ fontWeight: 600, fontSize: "0.65rem", height: 20, ...sx }}
  />
);

const PickCard = ({ pick }: { pick: SuggestedPick }) => {
  const confColor = getPickColor(pick.probability || pick.confidence || 0);
  const isCorrect = pick.was_correct;

  return (
    <Card
      sx={{
        background: isCorrect
          ? "linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.1) 100%)"
          : "linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.1) 100%)",
        border: `1px solid ${
          isCorrect ? "rgba(16, 185, 129, 0.3)" : "rgba(239, 68, 68, 0.3)"
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
              flexWrap: "wrap",
            }}
          >
            <span style={{ fontSize: "1.2em" }}>
              {getMarketIcon(pick.market_type)}
            </span>{" "}
            {pick.market_label || getMarketLabel(pick.market_type)}
            {pick.is_contrarian && (
              <PickChip
                label="VALOR"
                sx={{
                  bgcolor: "rgba(139, 92, 246, 0.5)", // Violet 500 @ 50%
                  color: "#ffffff",
                  border: "1px solid #8b5cf6",
                }}
              />
            )}
          </Typography>
          {isCorrect ? (
            <CheckCircle sx={{ fontSize: 20, color: "#10b981" }} />
          ) : (
            <Cancel sx={{ fontSize: 20, color: "#ef4444" }} />
          )}
        </Box>
        <Box display="flex" gap={1} flexWrap="wrap" alignItems="center">
          {
            /* Check for AI/ML status via flag OR reasoning text OR ml_confidence */
            (() => {
              const isAi =
                pick.is_ml_confirmed ||
                (pick.ml_confidence !== undefined && pick.ml_confidence > 0) ||
                (pick.reasoning &&
                  (pick.reasoning.includes("IA") ||
                    pick.reasoning.includes("ML") ||
                    pick.reasoning.includes("Smart Model")));

              if (isAi) {
                return (
                  <Box component="span">
                    <PickChip
                      label={isCorrect ? "IA ✅" : "IA ❌"}
                      icon={
                        <SmartToy
                          sx={{ fontSize: "14px !important", color: "#38bdf8" }}
                        />
                      }
                      sx={{
                        bgcolor: "rgba(56, 189, 248, 0.5)", // Sky 400 @ 50%
                        color: "#ffffff",
                        borderColor: "#38bdf8", // Sky 400
                        borderWidth: "1px",
                        fontWeight: 700,
                      }}
                    />
                  </Box>
                );
              }
              return null;
            })()
          }
          {pick.expected_value !== undefined && pick.expected_value > 0 && (
            <Tooltip
              title="EV (Valor Esperado): Rentabilidad teórica a largo plazo de esta apuesta. >0% es bueno."
              arrow
            >
              <Box component="span">
                <PickChip
                  label={`EV: +${pick.expected_value.toFixed(1)}%`}
                  sx={{
                    bgcolor: "rgba(245, 158, 11, 0.5)", // Amber 500 @ 50%
                    color: "#ffffff",
                    border: "1px solid #f59e0b",
                  }}
                />
              </Box>
            </Tooltip>
          )}
          <Box component="span">
            <PickChip
              label={`Conf: ${(
                (pick.probability || pick.confidence || 0) * 100
              ).toFixed(0)}%`}
              sx={{
                bgcolor: confColor + "80", // 50% opacity (hex 80 is ~50%)
                color: "#ffffff",
                border: `1px solid ${confColor}`,
              }}
            />
          </Box>
          {pick.suggested_stake !== undefined && pick.suggested_stake > 0 && (
            <Tooltip
              title="Stake (Apuesta sugerida): Unidades a apostar según el criterio de Kelly para optimizar el bankroll."
              arrow
            >
              <Box component="span">
                <PickChip
                  label={`Stake: ${pick.suggested_stake.toFixed(2)}u`}
                  sx={{
                    bgcolor: "rgba(14, 165, 233, 0.5)", // Sky 500 @ 50%
                    color: "#ffffff",
                    border: "1px solid #0ea5e9",
                  }}
                />
              </Box>
            </Tooltip>
          )}
          {pick.clv_beat !== undefined && (
            <Tooltip
              title="CLV (Valor de Línea de Cierre): Indica si la cuota que tomaste fue mejor que la cuota final del mercado. Ganar al CLV es el mejor indicador de éxito a largo plazo."
              arrow
            >
              <Box component="span">
                <PickChip
                  label={pick.clv_beat ? "CLV ✅" : "CLV ❌"}
                  sx={{
                    bgcolor: pick.clv_beat
                      ? "rgba(16, 185, 129, 0.5)" // Emerald 500 @ 50%
                      : "rgba(239, 68, 68, 0.5)", // Red 500 @ 50%
                    color: "#ffffff",
                    border: pick.clv_beat
                      ? "1px solid #10b981"
                      : "1px solid #ef4444",
                  }}
                />
              </Box>
            </Tooltip>
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

// --- Helper for AI Detection ---
const isAiPick = (pick: SuggestedPick): boolean => {
  return !!(
    pick.is_ml_confirmed ||
    (pick.ml_confidence !== undefined && pick.ml_confidence > 0) ||
    (pick.reasoning &&
      (pick.reasoning.includes("IA") ||
        pick.reasoning.includes("ML") ||
        pick.reasoning.includes("Smart Model")))
  );
};

const ExpandedMatchDetails = ({ match }: { match: MatchPredictionHistory }) => {
  const uniquePicks = getUniquePicks(match.picks || []);
  const correctCount = uniquePicks.filter((p) => p.was_correct).length;
  const wrongCount = uniquePicks.filter((p) => !p.was_correct).length;

  const aiPicks = uniquePicks.filter(isAiPick);
  const aiCorrectCount = aiPicks.filter((p) => p.was_correct).length;
  const aiWrongCount = aiPicks.filter((p) => !p.was_correct).length;

  return (
    <Box sx={{ p: 3, bgcolor: "rgba(15, 23, 42, 0.6)" }}>
      <Box
        display="flex"
        alignItems="center"
        justifyContent="space-between"
        mb={2}
      >
        <Typography variant="h6" fontWeight={700} color="white">
          📊 Todos los Picks del Partido
        </Typography>
        <Box display="flex" gap={1}>
          {/* Total Stats */}
          <PickChip
            icon={<CheckCircle sx={{ fontSize: "16px !important" }} />}
            label={`${correctCount} Aciertos`}
            sx={{
              bgcolor: "rgba(16, 185, 129, 0.1)",
              color: "#10b981",
              border: "1px solid rgba(16, 185, 129, 0.2)",
              height: 24,
            }}
          />
          <PickChip
            icon={<Cancel sx={{ fontSize: "16px !important" }} />}
            label={`${wrongCount} Fallos`}
            sx={{
              bgcolor: "rgba(239, 68, 68, 0.1)",
              color: "#ef4444",
              border: "1px solid rgba(239, 68, 68, 0.2)",
              height: 24,
            }}
          />

          {/* AI Specific Stats */}
          {(aiCorrectCount > 0 || aiWrongCount > 0) && (
            <>
              <Box mx={1} width="1px" bgcolor="rgba(255,255,255,0.2)" />
              <PickChip
                icon={<SmartToy sx={{ fontSize: "14px !important" }} />}
                label={`IA: ${aiCorrectCount} ✅`}
                sx={{
                  bgcolor: "rgba(56, 189, 248, 0.15)",
                  color: "#38bdf8",
                  borderColor: "#38bdf8",
                  borderWidth: "1px",
                  height: 24,
                }}
              />
              <PickChip
                label={`IA: ${aiWrongCount} ❌`}
                sx={{
                  bgcolor: "rgba(56, 189, 248, 0.05)",
                  color: "rgba(255,255,255,0.7)",
                  borderColor: "rgba(56, 189, 248, 0.3)",
                  borderWidth: "1px",
                  height: 24,
                }}
              />
            </>
          )}
        </Box>
      </Box>
      <Grid container spacing={2}>
        {uniquePicks
          .sort(
            (a, b) =>
              (b.probability || b.confidence || 0) -
              (a.probability || a.confidence || 0)
          )
          .map((pick, index) => (
            <Grid size={{ xs: 12, sm: 6, md: 4 }} key={index}>
              <PickCard pick={pick} />
            </Grid>
          ))}
      </Grid>
    </Box>
  );
};

// --- Desktop Components ---
const DesktopMatchRow = ({
  match,
  isExpanded,
  onToggleExpand,
}: {
  match: MatchPredictionHistory;
  isExpanded: boolean;
  onToggleExpand: (id: string) => void;
}) => (
  <>
    <TableRow
      sx={{
        "&:hover": {
          bgcolor: "rgba(148, 163, 184, 0.05)",
          cursor: match.picks?.length > 0 ? "pointer" : "default",
        },
        "& td, & th": { borderBottom: isExpanded ? "none" : undefined },
      }}
      onClick={() => match.picks?.length > 0 && onToggleExpand(match.match_id)}
    >
      <TableCell sx={{ width: 48, p: 1 }}>
        {match.picks?.length > 0 && (
          <IconButton
            size="small"
            sx={{
              color: "#6366f1",
              transition: "transform 0.3s ease",
              transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
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
        <Typography variant="body2" fontWeight={700} sx={{ color: "#10b981" }}>
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
          <PickChip
            icon={<CheckCircle />}
            label="Correcta"
            color="success"
            sx={{ borderColor: "rgba(34, 197, 94, 0.3)", color: "#10b981" }}
          />
        ) : (
          <PickChip
            icon={<Cancel />}
            label="Errada"
            color="error"
            sx={{ borderColor: "rgba(239, 68, 68, 0.3)", color: "#ef4444" }}
          />
        )}
      </TableCell>
    </TableRow>
    {match.picks?.length > 0 && (
      <TableRow>
        <TableCell colSpan={7} sx={{ p: 0, border: 0 }}>
          <Collapse in={isExpanded} timeout="auto" unmountOnExit>
            <ExpandedMatchDetails match={match} />
          </Collapse>
        </TableCell>
      </TableRow>
    )}
  </>
);

// --- Mobile Components ---
const MobileMatchCard = ({
  match,
  isExpanded,
  onToggleExpand,
}: {
  match: MatchPredictionHistory;
  isExpanded: boolean;
  onToggleExpand: (id: string) => void;
}) => {
  const uniquePicks = getUniquePicks(match.picks || []);
  const correctCount = uniquePicks.filter((p) => p.was_correct).length;
  const wrongCount = uniquePicks.filter((p) => !p.was_correct).length;

  const aiPicks = uniquePicks.filter(isAiPick);
  const aiCorrectCount = aiPicks.filter((p) => p.was_correct).length;
  const aiWrongCount = aiPicks.filter((p) => !p.was_correct).length;

  return (
    <Card
      sx={{
        mb: 2,
        background:
          "linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)",
        backdropFilter: "blur(20px)",
        border: "1px solid rgba(148, 163, 184, 0.2)",
        borderRadius: 3, // More rounded
        boxShadow:
          "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
      }}
    >
      <CardContent sx={{ p: 2 }}>
        {/* Header: Date + Status */}
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          mb={2}
          pb={1.5}
          borderBottom="1px solid rgba(255,255,255,0.05)"
        >
          <Typography
            variant="caption"
            color="text.secondary"
            fontWeight={600}
            letterSpacing={0.5}
          >
            {formatDate(match.match_date)}
          </Typography>
          {match.was_correct ? (
            <PickChip
              icon={<CheckCircle />}
              label="ACIERTO"
              color="success"
              sx={{
                borderColor: "rgba(34, 197, 94, 0.5)",
                color: "#4ade80",
                fontSize: "0.65rem",
                height: 22,
                bgcolor: "rgba(34, 197, 94, 0.1)",
              }}
            />
          ) : (
            <PickChip
              icon={<Cancel />}
              label="FALLO"
              color="error"
              sx={{
                borderColor: "rgba(239, 68, 68, 0.5)",
                color: "#f87171",
                fontSize: "0.65rem",
                height: 22,
                bgcolor: "rgba(239, 68, 68, 0.1)",
              }}
            />
          )}
        </Box>

        {/* Main Content: Teams & Score */}
        <Box mb={2} textAlign="center">
          <Typography
            variant="body1"
            fontWeight={700}
            color="white"
            sx={{ fontSize: "1.05rem", lineHeight: 1.3, mb: 1 }}
          >
            {match.home_team}{" "}
            <span style={{ color: "rgba(255,255,255,0.4)", fontWeight: 400 }}>
              vs
            </span>{" "}
            {match.away_team}
          </Typography>

          <Box
            display="inline-block"
            px={2}
            py={0.5}
            bgcolor="rgba(16, 185, 129, 0.1)"
            borderRadius={2}
            border="1px solid rgba(16, 185, 129, 0.2)"
          >
            <Typography
              variant="h6"
              fontWeight={800}
              sx={{ color: "#34d399", letterSpacing: 2 }}
            >
              {match.actual_home_goals} - {match.actual_away_goals}
            </Typography>
          </Box>
        </Box>

        {/* Prediction Row */}
        <Box
          display="flex"
          justifyContent="space-between"
          alignItems="center"
          bgcolor="rgba(255,255,255,0.03)"
          p={1.5}
          borderRadius={2}
          mb={2}
        >
          <Typography variant="caption" color="text.secondary">
            Predicción:
          </Typography>
          <Box textAlign="right">
            <Typography
              variant="body2"
              fontWeight={700}
              color="rgba(255,255,255,0.95)"
            >
              {getPredictionLabel(
                match.predicted_winner,
                match.home_team,
                match.away_team
              )}
            </Typography>
            <Typography
              variant="caption"
              color="text.disabled"
              fontWeight={500}
            >
              (Esperado: {match.predicted_home_goals.toFixed(1)} -{" "}
              {match.predicted_away_goals.toFixed(1)})
            </Typography>
          </Box>
        </Box>

        {/* Expandable Picks Section */}
        {match.picks?.length > 0 && (
          <Box mt={0}>
            {/* Toggle Header */}
            <Box
              display="flex"
              justifyContent="space-between"
              alignItems="center"
              onClick={() => onToggleExpand(match.match_id)}
              sx={{
                cursor: "pointer",
                py: 1,
                px: 0.5,
                borderRadius: 1,
                "&:active": { bgcolor: "rgba(255,255,255,0.03)" },
              }}
            >
              <Box display="flex" alignItems="center" gap={1}>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  fontWeight={700}
                  sx={{ textTransform: "uppercase" }}
                >
                  Picks ({uniquePicks.length})
                </Typography>
              </Box>

              <Box display="flex" alignItems="center" gap={1.5}>
                {/* Count Correct/Wrong */}
                <Box display="flex" gap={1}>
                  <Box display="flex" alignItems="center" gap={0.5}>
                    <CheckCircle sx={{ fontSize: 14, color: "#34d399" }} />
                    <Typography
                      variant="caption"
                      fontWeight={700}
                      color="#34d399"
                    >
                      {correctCount}
                    </Typography>
                  </Box>
                  <Box display="flex" alignItems="center" gap={0.5}>
                    <Cancel sx={{ fontSize: 14, color: "#f87171" }} />
                    <Typography
                      variant="caption"
                      fontWeight={700}
                      color="#f87171"
                    >
                      {wrongCount}
                    </Typography>
                  </Box>
                </Box>

                {/* AI Counts */}
                {(aiCorrectCount > 0 || aiWrongCount > 0) && (
                  <Box
                    display="flex"
                    alignItems="center"
                    gap={0.5}
                    pl={1.5}
                    borderLeft="1px solid rgba(255,255,255,0.15)"
                  >
                    <SmartToy sx={{ fontSize: 14, color: "#38bdf8" }} />
                    <Typography
                      variant="caption"
                      fontWeight={700}
                      color="#38bdf8"
                    >
                      {aiCorrectCount}/{aiWrongCount}
                    </Typography>
                  </Box>
                )}

                <KeyboardArrowDown
                  sx={{
                    fontSize: 20,
                    color: "rgba(255,255,255,0.5)",
                    transition: "transform 0.3s ease",
                    transform: isExpanded ? "rotate(180deg)" : "rotate(0deg)",
                    ml: 0.5,
                  }}
                />
              </Box>
            </Box>

            <Collapse in={isExpanded} timeout="auto" unmountOnExit>
              <Box mt={1.5} display="flex" flexDirection="column" gap={1.5}>
                {uniquePicks
                  .sort(
                    (a, b) =>
                      (b.probability || b.confidence || 0) -
                      (a.probability || a.confidence || 0)
                  )
                  .map((pick, index) => (
                    <PickCard key={index} pick={pick} />
                  ))}
              </Box>
            </Collapse>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

// --- Main Container Component ---

const MatchHistoryTable: React.FC<MatchHistoryTableProps> = (props) => {
  const {
    page,
    rowsPerPage,
    searchQuery,
    expandedRow,
    sortColumn,
    sortDirection,
    paginatedMatches,
    totalMatches,
    isEmpty,
    handleSort,
    handleChangePage,
    handleChangeRowsPerPage,
    handleSearchChange,
    handleToggleExpand,
  } = useMatchHistoryTable(props);

  if (isEmpty) {
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
      <Box mb={3}>
        <TextField
          fullWidth
          variant="outlined"
          placeholder="Buscar equipo..."
          value={searchQuery}
          onChange={handleSearchChange}
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
                <TableCell sx={{ color: "text.secondary", fontWeight: 600 }}>
                  <TableSortLabel
                    active={sortColumn === "date"}
                    direction={sortColumn === "date" ? sortDirection : "desc"}
                    onClick={() => handleSort("date")}
                    sx={{
                      color: "rgba(255,255,255,0.7) !important",
                      "&.Mui-active": { color: "#6366f1 !important" },
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
                      "&.Mui-active": { color: "#6366f1 !important" },
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
                <DesktopMatchRow
                  key={match.match_id}
                  match={match}
                  isExpanded={expandedRow === match.match_id}
                  onToggleExpand={handleToggleExpand}
                />
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <TablePagination
          rowsPerPageOptions={[10, 25, 50, 100]}
          component="div"
          count={totalMatches}
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
          <MobileMatchCard
            key={match.match_id}
            match={match}
            isExpanded={expandedRow === match.match_id}
            onToggleExpand={handleToggleExpand}
          />
        ))}
        <TablePagination
          rowsPerPageOptions={[10, 25, 50, 100]}
          component="div"
          count={totalMatches}
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

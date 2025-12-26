import React, { useMemo, useState } from "react";
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Chip,
  Paper,
  Tabs,
  Tab,
} from "@mui/material";
import { CheckCircle, Cancel, TrendingUp } from "@mui/icons-material";
import { MatchPredictionHistory } from "../../../types";

interface PicksStatsTableProps {
  matches: MatchPredictionHistory[];
  filterDate?: string;
}

interface PickStats {
  type: string;
  label: string;
  won: number;
  lost: number;
  total: number;
  hitRate: number;
  category: string;
}

// Category mapping for tabs uses market_type to determine which tab a pick belongs to
const getCategory = (marketType: string): string => {
  // Check specific categories first (antes de revisar substring)
  if (marketType.includes("btts")) {
    return "btts";
  }
  if (
    marketType === "winner" ||
    marketType === "draw" ||
    marketType === "result_1x2" ||
    marketType.includes("double_chance") ||
    marketType.includes("handicap")
  ) {
    return "resultado";
  }
  if (marketType.includes("corners")) {
    return "corners";
  }
  if (marketType.includes("cards") || marketType === "red_cards") {
    return "tarjetas";
  }
  if (marketType.includes("goals") || marketType.includes("team_goals")) {
    return "goles";
  }
  return "otros";
};

// Tab definitions
const TABS = [
  { id: "goles", label: "Goles ⚽" },
  { id: "corners", label: "Córners 🚩" },
  { id: "tarjetas", label: "Tarjetas 🟨" },
  { id: "resultado", label: "Resultado 🏆" },
  { id: "btts", label: "BTTS" },
];

const PicksStatsTable: React.FC<PicksStatsTableProps> = ({
  matches,
  filterDate,
}) => {
  const [activeTab, setActiveTab] = useState("goles");

  // Normalize label to use generic Local/Visitante instead of team names
  const normalizeLabel = (
    label: string,
    marketType: string,
    homeTeam?: string,
    awayTeam?: string
  ): string => {
    let normalized = label;

    // Helper to escape special regex characters in team names
    const escapeRegex = (str: string) =>
      str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

    // Replace specific team names with Local/Visitante
    if (homeTeam) {
      const escapedHome = escapeRegex(homeTeam);
      normalized = normalized.replace(new RegExp(escapedHome, "gi"), "Local");
    }
    if (awayTeam) {
      const escapedAway = escapeRegex(awayTeam);
      normalized = normalized.replace(
        new RegExp(escapedAway, "gi"),
        "Visitante"
      );
    }

    // For winner picks, replace "(1)" with "Local gana", "(2)" with "Visitante gana"
    if (marketType === "winner" || marketType === "draw") {
      if (normalized.includes("(1)")) {
        normalized = "Local gana";
      } else if (normalized.includes("(2)")) {
        normalized = "Visitante gana";
      } else if (
        normalized.toLowerCase().includes("empate") ||
        normalized.includes("(X)")
      ) {
        normalized = "Empate";
      }
    }

    // Normalize goals labels - distinguish between total and team goals
    if (marketType.includes("goals") || marketType.includes("team_goals")) {
      // Check if it's team-specific goals (has Local/Visitante after team name replacement)
      const hasLocal = normalized.toLowerCase().includes("local");
      const hasVisitante = normalized.toLowerCase().includes("visitante");

      // Extract the line value (1.5, 2.5, etc.)
      const lineMatch = normalized.match(/(\d+\.?\d*)/);
      const lineValue = lineMatch ? lineMatch[0] : "";

      // Determine if it's over or under
      const isOver =
        normalized.toLowerCase().includes("más") ||
        normalized.toLowerCase().includes("over") ||
        normalized.includes("+");
      const sign = isOver ? "+" : "-";

      if (hasLocal || hasVisitante) {
        // Team-specific goals: "Local - Goles +1.5"
        const team = hasLocal ? "Local" : "Visitante";
        normalized = `${team} - Goles ${sign}${lineValue}`;
      } else {
        // Total match goals: "Partido - Goles +2.5"
        normalized = `Partido - Goles ${sign}${lineValue}`;
      }
    }

    // Normalize corners labels
    if (marketType.includes("corners")) {
      const hasLocal = normalized.toLowerCase().includes("local");
      const hasVisitante = normalized.toLowerCase().includes("visitante");

      const lineMatch = normalized.match(/(\d+\.?\d*)/);
      const lineValue = lineMatch ? lineMatch[0] : "";

      const isOver =
        normalized.toLowerCase().includes("más") ||
        normalized.toLowerCase().includes("over") ||
        normalized.includes("+");
      const sign = isOver ? "+" : "-";

      if (hasLocal || hasVisitante) {
        const team = hasLocal ? "Local" : "Visitante";
        normalized = `${team} - Córners ${sign}${lineValue}`;
      } else {
        normalized = `Partido - Córners ${sign}${lineValue}`;
      }
    }

    // Normalize cards labels
    if (marketType.includes("cards") && !marketType.includes("red")) {
      const hasLocal = normalized.toLowerCase().includes("local");
      const hasVisitante = normalized.toLowerCase().includes("visitante");

      const lineMatch = normalized.match(/(\d+\.?\d*)/);
      const lineValue = lineMatch ? lineMatch[0] : "";

      const isOver =
        normalized.toLowerCase().includes("más") ||
        normalized.toLowerCase().includes("over") ||
        normalized.includes("+");
      const sign = isOver ? "+" : "-";

      if (hasLocal || hasVisitante) {
        const team = hasLocal ? "Local" : "Visitante";
        normalized = `${team} - Tarjetas ${sign}${lineValue}`;
      } else {
        normalized = `Partido - Tarjetas ${sign}${lineValue}`;
      }
    }

    // Clean up common patterns
    normalized = normalized
      .replace(/victoria\s+local/gi, "Local gana")
      .replace(/victoria\s+visitante/gi, "Visitante gana")
      .replace(/gana\s+\(1\)/gi, "Local gana")
      .replace(/gana\s+\(2\)/gi, "Visitante gana")
      .replace(/\s+/g, " ")
      .trim();

    return normalized;
  };

  const stats = useMemo<PickStats[]>(() => {
    const filteredMatches = filterDate
      ? matches.filter((m) => new Date(m.match_date) >= new Date(filterDate))
      : matches;

    // Group by normalized label for generic stats (e.g. "Goles Local +1.5")
    const pickLabelMap: Record<
      string,
      { won: number; lost: number; marketType: string }
    > = {};

    for (const match of filteredMatches) {
      if (!match.picks) continue;

      // Get team names from match for normalization
      const homeTeamRaw = match.home_team;
      const awayTeamRaw = match.away_team;
      const homeTeam =
        typeof homeTeamRaw === "string"
          ? homeTeamRaw
          : (homeTeamRaw as { name?: string })?.name;
      const awayTeam =
        typeof awayTeamRaw === "string"
          ? awayTeamRaw
          : (awayTeamRaw as { name?: string })?.name;

      for (const pick of match.picks) {
        const rawLabel = pick.market_label || pick.market_type || "unknown";
        const marketType = pick.market_type || "unknown";

        // Normalize the label to use Local/Visitante
        const label = normalizeLabel(rawLabel, marketType, homeTeam, awayTeam);

        if (!pickLabelMap[label]) {
          pickLabelMap[label] = { won: 0, lost: 0, marketType };
        }

        if (pick.was_correct === true) {
          pickLabelMap[label].won += 1;
        } else if (pick.was_correct === false) {
          pickLabelMap[label].lost += 1;
        }
      }
    }

    const result: PickStats[] = Object.entries(pickLabelMap)
      .map(([label, { won, lost, marketType }]) => ({
        type: marketType,
        label,
        won,
        lost,
        total: won + lost,
        hitRate: won + lost > 0 ? (won / (won + lost)) * 100 : 0,
        category: getCategory(marketType),
      }))
      .filter((s) => s.total > 0)
      .sort((a, b) => {
        // Extract base label (remove Local/Visitante for grouping)
        const getBaseLabel = (label: string) =>
          label
            .replace(/\s*(Local|Visitante)\s*/gi, " ")
            .replace(/\s+/g, " ")
            .trim();

        const baseA = getBaseLabel(a.label);
        const baseB = getBaseLabel(b.label);

        // Group by base label first
        if (baseA !== baseB) {
          // Sort alphabetically by base label
          return baseA.localeCompare(baseB, "es");
        }

        // Within same base, Local comes before Visitante
        const isLocalA = a.label.toLowerCase().includes("local");
        const isLocalB = b.label.toLowerCase().includes("local");
        if (isLocalA && !isLocalB) return -1;
        if (!isLocalA && isLocalB) return 1;

        // If no Local/Visitante distinction, sort by total (descending)
        return b.total - a.total;
      });

    return result;
  }, [matches, filterDate]);

  // Filter stats by active tab
  const filteredStats = useMemo(() => {
    return stats.filter((s) => s.category === activeTab);
  }, [stats, activeTab]);

  // Calculate totals for filtered stats
  const totals = useMemo(() => {
    const won = filteredStats.reduce((sum, s) => sum + s.won, 0);
    const lost = filteredStats.reduce((sum, s) => sum + s.lost, 0);
    const total = won + lost;
    return {
      won,
      lost,
      total,
      hitRate: total > 0 ? (won / total) * 100 : 0,
    };
  }, [filteredStats]);

  // Count picks per category for tab badges
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = { todos: 0 };
    for (const s of stats) {
      counts[s.category] = (counts[s.category] || 0) + s.total;
      counts.todos += s.total;
    }
    return counts;
  }, [stats]);

  if (stats.length === 0) {
    return (
      <Box
        sx={{
          p: 3,
          textAlign: "center",
          color: "rgba(255,255,255,0.5)",
        }}
      >
        <Typography variant="body2">
          No hay datos de picks para mostrar
        </Typography>
      </Box>
    );
  }

  return (
    <Box>
      {/* Category Tabs */}
      <Tabs
        value={activeTab}
        onChange={(_, newValue) => setActiveTab(newValue)}
        variant="scrollable"
        scrollButtons="auto"
        sx={{
          mb: 2,
          "& .MuiTabs-indicator": {
            backgroundColor: "#fbbf24",
          },
          "& .MuiTab-root": {
            color: "rgba(255,255,255,0.5)",
            textTransform: "none",
            fontWeight: 600,
            minHeight: 40,
            "&.Mui-selected": {
              color: "#fbbf24",
            },
          },
        }}
      >
        {TABS.map((tab) => (
          <Tab
            key={tab.id}
            value={tab.id}
            label={
              <Box display="flex" alignItems="center" gap={1}>
                {tab.label}
                {categoryCounts[tab.id] > 0 && (
                  <Chip
                    label={categoryCounts[tab.id]}
                    size="small"
                    sx={{
                      height: 18,
                      fontSize: "0.65rem",
                      bgcolor:
                        activeTab === tab.id
                          ? "rgba(251, 191, 36, 0.2)"
                          : "rgba(255,255,255,0.1)",
                      color:
                        activeTab === tab.id
                          ? "#fbbf24"
                          : "rgba(255,255,255,0.7)",
                    }}
                  />
                )}
              </Box>
            }
          />
        ))}
      </Tabs>

      {/* Stats Table */}
      {filteredStats.length === 0 ? (
        <Box sx={{ p: 2, textAlign: "center", color: "rgba(255,255,255,0.5)" }}>
          <Typography variant="body2">
            No hay picks en esta categoría
          </Typography>
        </Box>
      ) : (
        <TableContainer
          component={Paper}
          sx={{
            bgcolor: "transparent",
            boxShadow: "none",
            "& .MuiTableCell-root": {
              borderColor: "rgba(148, 163, 184, 0.1)",
              py: 1.5,
            },
          }}
        >
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell
                  sx={{
                    color: "rgba(255,255,255,0.7)",
                    fontWeight: 600,
                    position: "sticky",
                    left: 0,
                    zIndex: 5,
                    bgcolor: "#1e293b",
                  }}
                >
                  Tipo de Pick
                </TableCell>
                <TableCell
                  align="center"
                  sx={{ color: "rgba(255,255,255,0.7)", fontWeight: 600 }}
                >
                  <Box
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                    gap={0.5}
                  >
                    <CheckCircle sx={{ fontSize: 16, color: "#22c55e" }} />
                    Ganados
                  </Box>
                </TableCell>
                <TableCell
                  align="center"
                  sx={{ color: "rgba(255,255,255,0.7)", fontWeight: 600 }}
                >
                  <Box
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                    gap={0.5}
                  >
                    <Cancel sx={{ fontSize: 16, color: "#ef4444" }} />
                    Perdidos
                  </Box>
                </TableCell>
                <TableCell
                  align="center"
                  sx={{ color: "rgba(255,255,255,0.7)", fontWeight: 600 }}
                >
                  Total
                </TableCell>
                <TableCell
                  align="center"
                  sx={{ color: "rgba(255,255,255,0.7)", fontWeight: 600 }}
                >
                  <Box
                    display="flex"
                    alignItems="center"
                    justifyContent="center"
                    gap={0.5}
                  >
                    <TrendingUp sx={{ fontSize: 16, color: "#fbbf24" }} />%
                    Acierto
                  </Box>
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {filteredStats.map((stat) => (
                <TableRow
                  key={stat.label}
                  sx={{
                    "&:hover": {
                      bgcolor: "rgba(148, 163, 184, 0.05)",
                    },
                  }}
                >
                  <TableCell
                    sx={{
                      color: "white",
                      position: "sticky",
                      left: 0,
                      zIndex: 1,
                      bgcolor: "#1e293b",
                    }}
                  >
                    <Typography variant="body2" fontWeight={500}>
                      {stat.label}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2" sx={{ color: "#22c55e" }}>
                      {stat.won}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2" sx={{ color: "#ef4444" }}>
                      {stat.lost}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Typography variant="body2" sx={{ color: "white" }}>
                      {stat.total}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={`${stat.hitRate.toFixed(1)}%`}
                      size="small"
                      sx={{
                        bgcolor:
                          stat.hitRate >= 55
                            ? "rgba(34, 197, 94, 0.2)"
                            : stat.hitRate >= 45
                            ? "rgba(251, 191, 36, 0.2)"
                            : "rgba(239, 68, 68, 0.2)",
                        color:
                          stat.hitRate >= 55
                            ? "#22c55e"
                            : stat.hitRate >= 45
                            ? "#fbbf24"
                            : "#ef4444",
                        fontWeight: 600,
                        minWidth: 65,
                      }}
                    />
                  </TableCell>
                </TableRow>
              ))}

              {/* Totals row */}
              <TableRow
                sx={{
                  bgcolor: "rgba(148, 163, 184, 0.1)",
                  "& .MuiTableCell-root": {
                    borderTop: "1px solid rgba(148, 163, 184, 0.3)",
                  },
                }}
              >
                <TableCell
                  sx={{
                    color: "white",
                    position: "sticky",
                    left: 0,
                    zIndex: 1,
                    bgcolor: "#1e293b",
                  }}
                >
                  <Typography variant="body2" fontWeight={700}>
                    TOTAL
                  </Typography>
                </TableCell>
                <TableCell align="center">
                  <Typography
                    variant="body2"
                    sx={{ color: "#22c55e", fontWeight: 700 }}
                  >
                    {totals.won}
                  </Typography>
                </TableCell>
                <TableCell align="center">
                  <Typography
                    variant="body2"
                    sx={{ color: "#ef4444", fontWeight: 700 }}
                  >
                    {totals.lost}
                  </Typography>
                </TableCell>
                <TableCell align="center">
                  <Typography
                    variant="body2"
                    sx={{ color: "white", fontWeight: 700 }}
                  >
                    {totals.total}
                  </Typography>
                </TableCell>
                <TableCell align="center">
                  <Chip
                    label={`${totals.hitRate.toFixed(1)}%`}
                    size="small"
                    sx={{
                      bgcolor:
                        totals.hitRate >= 55
                          ? "rgba(34, 197, 94, 0.3)"
                          : totals.hitRate >= 45
                          ? "rgba(251, 191, 36, 0.3)"
                          : "rgba(239, 68, 68, 0.3)",
                      color:
                        totals.hitRate >= 55
                          ? "#22c55e"
                          : totals.hitRate >= 45
                          ? "#fbbf24"
                          : "#ef4444",
                      fontWeight: 700,
                      minWidth: 65,
                    }}
                  />
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default PicksStatsTable;

import React from "react";
import { Box, Typography, Tooltip } from "@mui/material";
import { MatchPredictionHistory, SuggestedPick } from "../../../types";

export interface MarketPerformanceChartProps {
  history: MatchPredictionHistory[];
}

interface MarketStats {
  name: string;
  correct: number;
  incorrect: number;
  total: number;
  winRate: number;
}

const MarketPerformanceChart: React.FC<MarketPerformanceChartProps> = ({
  history,
}) => {
  const data = React.useMemo<MarketStats[]>(() => {
    const stats = {
      Winner: { correct: 0, total: 0 },
      Goals: { correct: 0, total: 0 },
      Corners: { correct: 0, total: 0 },
      Cards: { correct: 0, total: 0 },
    };

    history.forEach((match) => {
      if (match.picks && Array.isArray(match.picks)) {
        match.picks.forEach((pick: SuggestedPick) => {
          let category: keyof typeof stats | null = null;
          const type = pick.market_type;

          if (["winner", "draw", "double_chance", "va_handicap"].includes(type))
            category = "Winner";
          else if (["goals_over", "goals_under"].includes(type))
            category = "Goals";
          else if (["corners_over", "corners_under"].includes(type))
            category = "Corners";
          else if (["cards_over", "cards_under", "red_cards"].includes(type))
            category = "Cards";

          if (category) {
            stats[category].total++;
            if (pick.was_correct) stats[category].correct++;
          }
        });
      }
    });

    return Object.entries(stats).map(([name, val]) => ({
      name,
      correct: val.correct,
      incorrect: val.total - val.correct,
      total: val.total,
      winRate: val.total > 0 ? (val.correct / val.total) * 100 : 0,
    }));
  }, [history]);

  if (data.length === 0) return null;

  const maxTotal = Math.max(...data.map((d) => d.total));

  return (
    <Box
      sx={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "stretch",
        justifyContent: "space-around",
        px: 1,
        pb: 1,
      }}
    >
      {data.map((item) => {
        const correctHeight =
          maxTotal > 0 ? (item.correct / maxTotal) * 100 : 0;
        const incorrectHeight =
          maxTotal > 0 ? (item.incorrect / maxTotal) * 100 : 0;

        return (
          <Box
            key={item.name}
            sx={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              width: "20%",
            }}
          >
            <Tooltip
              title={
                <Box sx={{ textAlign: "center" }}>
                  <Typography
                    variant="caption"
                    display="block"
                    fontWeight="bold"
                  >
                    {item.name}
                  </Typography>
                  <Typography variant="body2" color="#22c55e">
                    Aciertos: {item.correct}
                  </Typography>
                  <Typography variant="body2" color="#ef4444">
                    Fallos: {item.incorrect}
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    Win Rate: {item.winRate.toFixed(1)}%
                  </Typography>
                </Box>
              }
              arrow
              placement="top"
            >
              <Box
                sx={{
                  width: "100%",
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "flex-end",
                  position: "relative",
                  cursor: "pointer",
                  minHeight: 0,
                }}
              >
                {/* Incorrect Bar (Top) */}
                {item.incorrect > 0 && (
                  <Box
                    sx={{
                      width: "100%",
                      height: `${incorrectHeight}%`,
                      bgcolor: "#ef4444",
                      opacity: 0.8,
                      borderTopLeftRadius: 4,
                      borderTopRightRadius: 4,
                      borderBottomLeftRadius: item.correct === 0 ? 4 : 0,
                      borderBottomRightRadius: item.correct === 0 ? 4 : 0,
                      transition: "all 0.3s",
                      "&:hover": { opacity: 1 },
                    }}
                  />
                )}
                {/* Correct Bar (Bottom) */}
                {item.correct > 0 && (
                  <Box
                    sx={{
                      width: "100%",
                      height: `${correctHeight}%`,
                      bgcolor: "#22c55e",
                      opacity: 0.9,
                      borderBottomLeftRadius: 4,
                      borderBottomRightRadius: 4,
                      borderTopLeftRadius: item.incorrect === 0 ? 4 : 0,
                      borderTopRightRadius: item.incorrect === 0 ? 4 : 0,
                      transition: "all 0.3s",
                      "&:hover": { opacity: 1 },
                    }}
                  />
                )}
              </Box>
            </Tooltip>
            <Typography
              variant="caption"
              sx={{
                mt: 1,
                color: "text.secondary",
                fontWeight: 600,
                fontSize: "0.7rem",
              }}
            >
              {item.name}
            </Typography>
            <Typography
              variant="caption"
              sx={{
                color: item.winRate >= 50 ? "#22c55e" : "#ef4444",
                fontWeight: 700,
              }}
            >
              {item.winRate.toFixed(0)}%
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
};

export default MarketPerformanceChart;

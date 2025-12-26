import React from "react";
import { Box, Typography, Tooltip, Chip } from "@mui/material";
import { TrendingUp, TrendingDown, TrendingFlat } from "@mui/icons-material";

export interface RoiEvolutionChartProps {
  data: { date: string; roi: number }[];
}

const RoiEvolutionChart: React.FC<RoiEvolutionChartProps> = ({ data }) => {
  if (!data || data.length === 0) return null;

  const rois = data.map((d) => d.roi);
  const minRoiValue = Math.min(...rois);
  const maxRoiValue = Math.max(...rois);
  const currentRoi = data[data.length - 1].roi;
  const previousRoi = data.length > 1 ? data[data.length - 2].roi : currentRoi;
  const trend = currentRoi - previousRoi;

  // Ensure we always include 0 in the y-axis for context
  const minRoi = Math.min(0, minRoiValue);
  const maxRoi = Math.max(0, maxRoiValue);

  // Handle case where all values are the same
  const range = maxRoi - minRoi;
  // Ensure minimum range of 10% to show something meaningful
  const effectiveRange = range === 0 ? 10 : range;
  const padding = effectiveRange * 0.1;
  const yMin = minRoi - padding;
  const yMax = maxRoi + padding;
  const yRange = yMax - yMin;

  const points = data
    .map((d, i) => {
      const x = (i / (data.length - 1)) * 100;
      const y = 100 - ((d.roi - yMin) / yRange) * 100;
      return `${x},${y}`;
    })
    .join(" ");

  const areaPoints = `${points} 100,100 0,100`;
  const zeroY = 100 - ((0 - yMin) / yRange) * 100;
  const lineColor = currentRoi >= 0 ? "#22c55e" : "#ef4444";

  // Grid lines calculation
  const gridLines = [0, 0.25, 0.5, 0.75, 1].map((p) => {
    const val = yMin + p * yRange;
    const y = 100 - p * 100;
    return { val, y };
  });

  return (
    <Box
      sx={{
        width: "100%",
        height: "100%",
        position: "relative",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Stats Summary */}
      {/* Stats Summary */}
      <Box
        sx={{
          display: "flex",
          gap: { xs: 1.5, sm: 2 },
          mb: 2,
          flexWrap: "wrap",
          alignItems: "center",
          width: "100%",
        }}
      >
        <Chip
          icon={
            trend > 0.5 ? (
              <TrendingUp />
            ) : trend < -0.5 ? (
              <TrendingDown />
            ) : (
              <TrendingFlat />
            )
          }
          label={`ROI Actual: ${currentRoi > 0 ? "+" : ""}${currentRoi.toFixed(
            2
          )}%`}
          sx={{
            bgcolor:
              currentRoi >= 0 ? "rgba(34,197,94,0.2)" : "rgba(239,68,68,0.2)",
            color: currentRoi >= 0 ? "#22c55e" : "#ef4444",
            fontWeight: 700,
            fontSize: "0.85rem",
            width: { xs: "100%", sm: "auto" }, // Full width on mobile
            justifyContent: { xs: "center", sm: "flex-start" },
            "& .MuiChip-icon": {
              color: "inherit",
            },
          }}
        />

        {/* Secondary Stats Group */}
        <Box
          sx={{
            display: "flex",
            gap: 2,
            alignItems: "center",
            flexWrap: "wrap",
            justifyContent: { xs: "space-between", sm: "flex-start" },
            width: { xs: "100%", sm: "auto" },
            mt: { xs: 0.5, sm: 0 },
            px: { xs: 0.5, sm: 0 },
          }}
        >
          <Typography variant="caption" color="text.secondary">
            Máx:{" "}
            <span style={{ color: "#22c55e", fontWeight: 600 }}>
              {maxRoiValue > 0 ? "+" : ""}
              {maxRoiValue.toFixed(2)}%
            </span>
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Mín:{" "}
            <span style={{ color: "#ef4444", fontWeight: 600 }}>
              {minRoiValue.toFixed(2)}%
            </span>
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Muestras: <span style={{ fontWeight: 600 }}>{data.length}</span>
          </Typography>
        </Box>
      </Box>

      <Box sx={{ flex: 1, position: "relative", minHeight: 0 }}>
        {/* Y-Axis Labels */}
        {gridLines.map((line, i) => (
          <Typography
            key={i}
            variant="caption"
            sx={{
              position: "absolute",
              left: 0,
              top: `${line.y}%`,
              transform: "translateY(-50%)",
              color: "rgba(255,255,255,0.5)",
              fontSize: "0.7rem",
              textShadow: "0 1px 2px rgba(0,0,0,0.8)",
              pointerEvents: "none",
              zIndex: 1,
            }}
          >
            {line.val.toFixed(1)}%
          </Typography>
        ))}

        <svg
          width="100%"
          height="100%"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          style={{ overflow: "visible", marginLeft: 35 }}
        >
          <defs>
            <linearGradient id="chartGradientRoi" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={lineColor} stopOpacity={0.3} />
              <stop offset="100%" stopColor={lineColor} stopOpacity={0.02} />
            </linearGradient>
          </defs>

          {/* Grid Lines */}
          {gridLines.map((line, i) => (
            <line
              key={i}
              x1="0"
              y1={line.y}
              x2="100"
              y2={line.y}
              stroke="rgba(255,255,255,0.08)"
              strokeWidth="0.5"
              vectorEffect="non-scaling-stroke"
            />
          ))}

          {/* Zero Line */}
          <line
            x1="0"
            y1={zeroY}
            x2="100"
            y2={zeroY}
            stroke="rgba(255,255,255,0.4)"
            strokeWidth="1"
            strokeDasharray="6 3"
            vectorEffect="non-scaling-stroke"
          />

          {/* Area Fill */}
          <polygon points={areaPoints} fill="url(#chartGradientRoi)" />

          {/* Chart Line */}
          <polyline
            points={points}
            fill="none"
            stroke={lineColor}
            strokeWidth="2"
            vectorEffect="non-scaling-stroke"
            strokeLinejoin="round"
            strokeLinecap="round"
          />

          {/* Current Point Highlight */}
        </svg>

        {/* Current Point Highlight (CSS Positioned) */}
        <Box
          sx={{
            position: "absolute",
            left: "100%",
            top: `${100 - ((currentRoi - yMin) / yRange) * 100}%`,
            width: 8,
            height: 8,
            borderRadius: "50%",
            bgcolor: lineColor,
            border: "2px solid white",
            transform: "translate(-50%, -50%)",
            boxShadow: `0 0 6px ${lineColor}`,
            zIndex: 2,
            pointerEvents: "none",
          }}
        />

        {/* Interactive Overlay Points for Tooltips */}
        <Box
          sx={{
            position: "absolute",
            top: 0,
            left: 35,
            right: 0,
            height: "100%",
            pointerEvents: "none",
          }}
        >
          {data.map((d, i) => {
            const x = (i / (data.length - 1)) * 100;
            const y = 100 - ((d.roi - yMin) / yRange) * 100;
            const color = d.roi >= 0 ? "#22c55e" : "#ef4444";

            return (
              <Tooltip
                key={i}
                title={
                  <Box sx={{ textAlign: "center", p: 0.5 }}>
                    <Typography
                      variant="caption"
                      display="block"
                      color="rgba(255,255,255,0.7)"
                    >
                      {d.date}
                    </Typography>
                    <Typography variant="body2" fontWeight={700} color="white">
                      ROI: {d.roi > 0 ? "+" : ""}
                      {d.roi.toFixed(2)}%
                    </Typography>
                  </Box>
                }
                arrow
                placement="top"
              >
                <Box
                  sx={{
                    position: "absolute",
                    left: `${x}%`,
                    top: `${y}%`,
                    width: 16,
                    height: 16,
                    transform: "translate(-50%, -50%)",
                    cursor: "crosshair",
                    pointerEvents: "auto",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    "&:hover .dot": {
                      opacity: 1,
                      transform: "scale(1.8)",
                      boxShadow: `0 0 12px ${color}`,
                    },
                  }}
                >
                  <Box
                    className="dot"
                    sx={{
                      width: 8,
                      height: 8,
                      borderRadius: "50%",
                      bgcolor: color,
                      border: "2px solid white",
                      opacity: 0,
                      transition: "all 0.2s ease",
                    }}
                  />
                </Box>
              </Tooltip>
            );
          })}
        </Box>

        {/* X-Axis Labels */}
        <Box
          display="flex"
          justifyContent="space-between"
          sx={{
            position: "absolute",
            bottom: 0,
            left: 35,
            right: 0,
            pointerEvents: "none",
          }}
        >
          <Typography
            variant="caption"
            color="rgba(255,255,255,0.5)"
            sx={{ textShadow: "0 1px 2px rgba(0,0,0,0.8)" }}
          >
            {data[0].date}
          </Typography>
          <Typography
            variant="caption"
            color="rgba(255,255,255,0.5)"
            sx={{ textShadow: "0 1px 2px rgba(0,0,0,0.8)" }}
          >
            {data[data.length - 1].date}
          </Typography>
        </Box>
      </Box>
    </Box>
  );
};

export default RoiEvolutionChart;

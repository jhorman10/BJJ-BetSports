import React from "react";
import { Box, Typography, Tooltip } from "@mui/material";

export interface RoiEvolutionChartProps {
  data: { date: string; roi: number }[];
}

const RoiEvolutionChart: React.FC<RoiEvolutionChartProps> = ({ data }) => {
  if (!data || data.length === 0) return null;

  const rois = data.map((d) => d.roi);
  const minRoi = Math.min(0, ...rois);
  const maxRoi = Math.max(...rois);

  const range = maxRoi - minRoi;
  const padding = range === 0 ? 1 : range * 0.02;
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
  const targetY = 100 - ((5 - yMin) / yRange) * 100;
  const showTarget = 5 >= yMin && 5 <= yMax;
  const lineColor = data[data.length - 1].roi >= 0 ? "#22c55e" : "#ef4444";

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
      <Box sx={{ flex: 1, position: "relative" }}>
        {/* Y-Axis Labels */}
        {gridLines.map((line, i) => (
          <Typography
            key={i}
            variant="caption"
            sx={{
              position: "absolute",
              left: 6,
              top: `${line.y}%`,
              transform: "translateY(-50%)",
              color: "rgba(255,255,255,0.5)",
              fontSize: "0.7rem",
              textShadow: "0 1px 2px rgba(0,0,0,0.8)",
              pointerEvents: "none",
              zIndex: 1,
            }}
          >
            {line.val.toFixed(0)}%
          </Typography>
        ))}

        {showTarget && (
          <Typography
            variant="caption"
            sx={{
              position: "absolute",
              right: 0,
              top: `${targetY}%`,
              transform: "translateY(-120%)",
              color: "#fbbf24",
              fontWeight: 700,
              fontSize: "0.7rem",
              pointerEvents: "none",
              textShadow: "0 2px 4px rgba(0,0,0,0.5)",
            }}
          >
            Target 5%
          </Typography>
        )}
        <svg
          width="100%"
          height="100%"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
          style={{ overflow: "visible" }}
        >
          <defs>
            <linearGradient id="chartGradient" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor={lineColor} stopOpacity={0.2} />
              <stop offset="100%" stopColor={lineColor} stopOpacity={0} />
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
              stroke="rgba(255,255,255,0.05)"
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
            stroke="rgba(255,255,255,0.3)"
            strokeWidth="1"
            strokeDasharray="4 4"
            vectorEffect="non-scaling-stroke"
          />

          {/* Target Line (5%) */}
          {showTarget && (
            <line
              x1="0"
              y1={targetY}
              x2="100"
              y2={targetY}
              stroke="#fbbf24"
              strokeWidth="1"
              strokeDasharray="4 4"
              vectorEffect="non-scaling-stroke"
              opacity={0.7}
            />
          )}

          {/* Area Fill */}
          <polygon points={areaPoints} fill="url(#chartGradient)" />

          {/* Chart Line */}
          <polyline
            points={points}
            fill="none"
            stroke={lineColor}
            strokeWidth="2.5"
            vectorEffect="non-scaling-stroke"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        </svg>

        {/* Interactive Overlay Points for Tooltips */}
        <Box
          sx={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
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
                    width: 12,
                    height: 12,
                    transform: "translate(-50%, -50%)",
                    cursor: "crosshair",
                    pointerEvents: "auto",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    "&:hover .dot": {
                      opacity: 1,
                      transform: "scale(1.5)",
                      boxShadow: `0 0 8px ${color}`,
                    },
                  }}
                >
                  <Box
                    className="dot"
                    sx={{
                      width: 6,
                      height: 6,
                      borderRadius: "50%",
                      bgcolor: color,
                      border: "1px solid white",
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
            bottom: 4,
            left: 6,
            right: 6,
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

import React from "react";
import { Box, Chip, Tooltip } from "@mui/material";
import Psychology from "@mui/icons-material/Psychology";
import PlayCircleOutline from "@mui/icons-material/PlayCircleOutline";
import AutoGraph from "@mui/icons-material/AutoGraph";
import Diamond from "@mui/icons-material/Diamond";

import type { MatchPrediction } from "../../../types";

interface MatchBadgesProps {
  prediction: MatchPrediction["prediction"];
  highlight?: boolean;
  hasRichData: boolean;
}

export const MatchBadges: React.FC<MatchBadgesProps> = ({
  prediction,
  highlight,
  hasRichData,
}) => (
  <>
    {/* Selection area badges when highlighted */}
    {highlight && (
      <Box
        sx={{
          position: "absolute",
          top: 12,
          right: 12,
          zIndex: 1,
          display: "flex",
          flexDirection: "row",
          gap: 0.5,
          alignItems: "center",
        }}
      >
        {prediction.data_sources.includes("Rigorous ML") && (
          <Tooltip title="Predicción generada por Modelo ML Riguroso">
            <Chip
              icon={<Psychology sx={{ fontSize: "0.9rem !important", color: "#ec4899 !important" }} />}
              label="ML"
              size="small"
              sx={{
                bgcolor: "rgba(236, 72, 153, 0.15)",
                color: "#ec4899",
                border: "1px solid rgba(236, 72, 153, 0.3)",
                fontWeight: 700,
                height: 24,
                "& .MuiChip-label": { px: 1 },
              }}
            />
          </Tooltip>
        )}
        <Chip
          label="Destacado"
          size="small"
          sx={{
            bgcolor: "#3b82f6",
            color: "#ffffff",
            fontWeight: 700,
            boxShadow: "0 0 15px rgba(59, 130, 246, 0.6)",
            border: "1px solid rgba(255, 255, 255, 0.2)",
          }}
        />
        {prediction.highlights_url && (
          <Chip
            icon={<PlayCircleOutline />}
            label="Highlights"
            clickable
            component="a"
            href={prediction.highlights_url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            size="small"
            sx={{
              bgcolor: "rgba(59, 130, 246, 0.3)",
              color: "#ffffff",
              border: "1px solid rgba(59, 130, 246, 0.5)",
              "&:hover": { bgcolor: "rgba(59, 130, 246, 0.5)" },
              "& .MuiChip-icon": { color: "#ffffff" },
            }}
          />
        )}
      </Box>
    )}

    {/* ML Badge (non-highlight) */}
    {prediction.data_sources.includes("Rigorous ML") && !highlight && (
      <Box
        sx={{
          position: "absolute",
          top: 12,
          right: hasRichData ? 80 : 12,
          zIndex: 1,
          mr: hasRichData ? 1 : 0,
        }}
      >
        <Tooltip title="Predicción generada por Modelo ML Riguroso">
          <Chip
            icon={<Psychology sx={{ fontSize: "0.9rem !important", color: "#ec4899 !important" }} />}
            label="ML"
            size="small"
            sx={{
              bgcolor: "rgba(236, 72, 153, 0.15)",
              color: "#ec4899",
              border: "1px solid rgba(236, 72, 153, 0.3)",
              fontWeight: 700,
              height: 24,
              "& .MuiChip-label": { px: 1 },
            }}
          />
        </Tooltip>
      </Box>
    )}

    {/* Rich Data Badge */}
    {hasRichData && !highlight && (
      <Box sx={{ position: "absolute", top: 12, right: 12, zIndex: 1 }}>
        <Tooltip title="Datos enriquecidos (Córners/Tarjetas) disponibles">
          <Chip
            icon={<AutoGraph sx={{ fontSize: "0.9rem !important", color: "#a78bfa !important" }} />}
            label="Data+"
            size="small"
            sx={{
              bgcolor: "rgba(139, 92, 246, 0.15)",
              color: "#a78bfa",
              border: "1px solid rgba(139, 92, 246, 0.3)",
              fontWeight: 700,
              height: 24,
              "& .MuiChip-label": { px: 1 },
            }}
          />
        </Tooltip>
      </Box>
    )}

    {/* Value Bet Badge */}
    {prediction.is_value_bet && (
      <Box
        sx={{
          position: "absolute",
          top: highlight ? 40 : hasRichData ? 40 : 12,
          right: 12,
          zIndex: 1,
        }}
      >
        <Chip
          icon={<Diamond sx={{ fontSize: "0.9rem !important" }} />}
          label={`EV +${((prediction.expected_value || 0) * 100).toFixed(1)}%`}
          size="small"
          sx={{
            bgcolor: "rgba(251, 191, 36, 0.2)",
            color: "#ffffff",
            border: "1px solid #fbbf24",
            fontWeight: 800,
            "& .MuiChip-icon": { color: "#fbbf24" },
          }}
        />
      </Box>
    )}
  </>
);

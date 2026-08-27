import React, { memo } from "react";
import { Box, Typography, Chip } from "@mui/material";
import { CheckCircle, Cancel, HourglassEmpty } from "@mui/icons-material";

import { SuggestedPick } from "../../../../types";
import { getPickColor, getMarketIcon } from "../../../../utils/marketUtils";
import { evaluatePickLive } from "../../../../utils/pickValidationUtils";
import { Match } from "../../../../domain/entities/match";

interface PickRowProps {
  pick: SuggestedPick;
  match?: Match;
}

export const PickRow: React.FC<PickRowProps> = memo(({ pick, match }) => {
  const color = getPickColor(pick.probability);

  return (
    <>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          py: 1,
          px: 1.5,
          borderLeft: `3px solid ${color}`,
          bgcolor: `${color}15`,
          borderRadius: "8px",
          mb: 1,
          transition: "all 0.2s ease",
          "&:hover": { bgcolor: `${color}25`, transform: "translateX(2px)" },
        }}
      >
        <Box display="flex" alignItems="center" gap={1} flex={1}>
          <Typography sx={{ fontSize: "1rem" }}>{getMarketIcon(pick.market_type)}</Typography>
          <Typography
            variant="body2"
            sx={{ fontWeight: 600, color: "#ffffff", fontSize: "0.85rem", wordBreak: "break-word", overflowWrap: "break-word" }}
          >
            {pick.market_label}
          </Typography>
          {(() => {
            if (!match) return null;
            const status = evaluatePickLive(pick, match);
            if (status === "WON") return <CheckCircle color="success" sx={{ fontSize: "1rem", ml: 0.5 }} />;
            if (status === "LOST") return <Cancel color="error" sx={{ fontSize: "1rem", ml: 0.5 }} />;
            if (status === "PENDING") return <HourglassEmpty color="warning" sx={{ fontSize: "1rem", ml: 0.5 }} />;
            return null;
          })()}
          {pick.is_ia_confirmed && (
            <Chip
              label="IA CONFIRMED"
              size="small"
              sx={{
                ml: 1,
                bgcolor: "rgba(37, 99, 235, 0.15)",
                color: "#60a5fa",
                borderColor: "#60a5fa",
                borderWidth: "1px",
                borderStyle: "solid",
                fontWeight: 900,
                fontSize: "0.65rem",
                height: 20,
                boxShadow: "0 0 8px rgba(37, 99, 235, 0.3)",
                "& .MuiChip-label": { px: 1 },
              }}
            />
          )}
          {!pick.is_ia_confirmed &&
            (pick.is_ml_confirmed ||
              (pick.ml_confidence !== undefined && pick.ml_confidence > 0.7) ||
              (pick.reasoning && pick.reasoning.includes("ML"))) && (
              <Chip
                label="ML Alta Confianza"
                size="small"
                sx={{
                  ml: 1,
                  bgcolor: "rgba(56, 189, 248, 0.15)",
                  color: "#38bdf8",
                  borderColor: "#38bdf8",
                  borderWidth: "1px",
                  borderStyle: "solid",
                  fontWeight: 700,
                  fontSize: "0.65rem",
                  height: 20,
                  "& .MuiChip-label": { px: 1 },
                }}
              />
            )}
        </Box>
        {pick.expected_value !== undefined && pick.expected_value > 0 && (
          <Chip
            label={`EV: +${pick.expected_value.toFixed(1)}%`}
            size="small"
            sx={{
              mr: 1,
              bgcolor: "rgba(245, 158, 11, 0.5)",
              color: "#ffffff",
              fontWeight: 700,
              fontSize: "0.70rem",
              height: 24,
              border: "1px solid #f59e0b",
              "& .MuiChip-label": { px: 1 },
            }}
          />
        )}
        {pick.suggested_stake !== undefined && pick.suggested_stake > 0 && (
          <Chip
            label={`Stake: ${pick.suggested_stake.toFixed(2)}u`}
            size="small"
            sx={{
              mr: 1,
              bgcolor: "rgba(14, 165, 233, 0.5)",
              color: "#ffffff",
              fontWeight: 700,
              fontSize: "0.70rem",
              height: 24,
              border: "1px solid #0ea5e9",
              "& .MuiChip-label": { px: 1 },
            }}
          />
        )}
        <Chip
          label={`${(pick.probability * 100).toFixed(0)}%`}
          size="small"
          sx={{
            bgcolor: color,
            color: "white",
            fontWeight: 700,
            fontSize: "0.75rem",
            height: 24,
            minWidth: 45,
            "& .MuiChip-label": { px: 1 },
          }}
        />
      </Box>
      {(pick.formatted_reasoning || pick.reasoning) && (
        <Typography
          variant="caption"
          sx={{
            display: "block",
            fontSize: "0.75rem",
            color: "rgba(255,255,255,0.6)",
            mt: -0.5,
            mb: 1.5,
            pl: 1,
            fontStyle: "italic",
            lineHeight: 1.4,
          }}
        >
          {(() => {
            let text = pick.formatted_reasoning || pick.reasoning || "";
            text = text.replace(/\[.*IA CONFIRMED\]/g, "").trim();
            text = text.replace(/\[.*TOP ML\]/g, "").trim();
            text = text.replace(/\[.*ML ALTA CONFIANZA\]/g, "").trim();
            text = text.replace(/\[.*NORMAL\]/g, "").trim();
            text = text.replace(/^[,.\s:]+|[,.\s:]+$/g, "");
            return text;
          })()}
        </Typography>
      )}
    </>
  );
});

PickRow.displayName = "PickRow";

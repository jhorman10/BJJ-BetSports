import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Slide,
  IconButton,
} from "@mui/material";
import { TransitionProps } from "@mui/material/transitions";
import { Close, SportsSoccer } from "@mui/icons-material";

import { useLiveStore } from "../../../application/stores/useLiveStore";
import { useUIStore } from "../../../application/stores/useUIStore";

import { LiveScoreBoard } from "./components/LiveScoreBoard";
import { LiveMatchStats } from "./components/LiveMatchStats";
import { PreMatchPrediction } from "./components/PreMatchPrediction";
import SuggestedPicksTab from "./SuggestedPicksTab";

const LiveMatchDetailsModal: React.FC = () => {
  const { liveModalOpen, selectedLiveMatch, closeLiveMatchModal } =
    useUIStore();
  const { matches: liveMatches } = useLiveStore();

  if (!liveModalOpen || !selectedLiveMatch) return null;

  // Find the latest version of the match from the live store for real-time score updates
  const liveMatchUpdate = liveMatches.find(
    (m) => m.match.id === selectedLiveMatch.match.id
  );

  // Always prefer live match stats (score, minute, corners) if available
  const match = liveMatchUpdate ? liveMatchUpdate.match : selectedLiveMatch.match;

  // Preserve the original prediction if the live update is just an ESPN stub (confidence = 0)
  const isLivePredictionValid =
    liveMatchUpdate &&
    (liveMatchUpdate.prediction.home_win_probability > 0 ||
      liveMatchUpdate.prediction.confidence > 0);

  const prediction = isLivePredictionValid
    ? liveMatchUpdate.prediction
    : selectedLiveMatch.prediction;

  // Fabricated fallback predictions (matchMatching stamps
  // ["live_match_fallback"]) must never render as a real pre-match
  // prediction — show the unavailable state instead.
  const isPredictionAvailable =
    (prediction.home_win_probability > 0 || prediction.confidence > 0) &&
    !prediction.data_sources?.includes("live_match_fallback");

  return (
    <Dialog
      open={liveModalOpen}
      onClose={closeLiveMatchModal}
      maxWidth="sm"
      fullWidth
      TransitionComponent={Slide}
      TransitionProps={{ direction: "up" } as TransitionProps}
      PaperProps={{
        sx: {
          width: { xs: "95%", sm: "100%" },
          margin: { xs: 1, sm: 2 },
          borderRadius: 2,
          maxHeight: { xs: "90vh", sm: "calc(100% - 64px)" },
          background: "linear-gradient(135deg, #1e293b 0%, #0f172a 100%)",
          color: "white",
        },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          pb: 1,
        }}
      >
        <Box display="flex" alignItems="center" gap={1}>
          <SportsSoccer color="primary" />
          <Typography component="span" variant="h6" fontWeight="bold">
            En Vivo
          </Typography>
        </Box>
        <IconButton onClick={closeLiveMatchModal} sx={{ color: "white" }}>
          <Close />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ overflowX: "visible", px: { xs: 1.5, sm: 3 } }}>
        {/* Live Score Board */}
        <LiveScoreBoard match={match} />

        {/* Live Stats Grid */}
        <LiveMatchStats match={match} />

        {/* Pre-match Prediction (Only if available) */}
        <PreMatchPrediction
          prediction={prediction}
          isAvailable={isPredictionAvailable}
          match={match}
        />

        {/* Suggested Picks with Live Validation */}
        {isPredictionAvailable && (
          <Box mt={3} pt={2} borderTop="1px solid rgba(255,255,255,0.1)">
            <Typography variant="subtitle1" fontWeight="bold" mb={2}>
              Picks y Resolución en Vivo
            </Typography>
            <SuggestedPicksTab matchPrediction={{ match, prediction }} />
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ p: 2 }}>
        <Button
          onClick={closeLiveMatchModal}
          variant="contained"
          color="primary"
          fullWidth
        >
          Cerrar
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default LiveMatchDetailsModal;

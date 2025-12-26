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

const LiveMatchDetailsModal: React.FC = () => {
  const { liveModalOpen, selectedLiveMatch, closeLiveMatchModal } =
    useUIStore();
  const { matches: liveMatches } = useLiveStore();

  if (!liveModalOpen || !selectedLiveMatch) return null;

  // Find the latest version of the match from the live store for real-time updates
  const latestMatch =
    liveMatches.find((m) => m.match.id === selectedLiveMatch.match.id) ||
    selectedLiveMatch;
  const { match, prediction } = latestMatch;
  const isPredictionAvailable =
    prediction.home_win_probability > 0 || prediction.confidence > 0;

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
          borderRadius: 2,
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
          <Typography variant="h6" fontWeight="bold">
            En Vivo
          </Typography>
        </Box>
        <IconButton onClick={closeLiveMatchModal} sx={{ color: "white" }}>
          <Close />
        </IconButton>
      </DialogTitle>

      <DialogContent>
        {/* Live Score Board */}
        <LiveScoreBoard match={match} />

        {/* Live Stats Grid */}
        <LiveMatchStats match={match} />

        {/* Pre-match Prediction (Only if available) */}
        <PreMatchPrediction
          prediction={prediction}
          isAvailable={isPredictionAvailable}
        />
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

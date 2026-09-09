import React from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  Chip,
  Divider,
  Slide,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { TransitionProps } from "@mui/material/transitions";

import { MatchPrediction } from "../../../types";

import SuggestedPicksTab from "./SuggestedPicksTab";
import { ScoreHeader } from "./components/ScoreHeader";
import { StatsGrid } from "./components/StatsGrid";
import { ProjectedStats } from "./components/ProjectedStats";
import { VideoHighlights } from "./components/VideoHighlights";
import { RecommendationBox } from "./components/RecommendationBox";

interface MatchDetailsModalProps {
  open: boolean;
  onClose: () => void;
  matchPrediction: MatchPrediction | null;
}

const MatchDetailsModal: React.FC<MatchDetailsModalProps> = ({
  open,
  onClose,
  matchPrediction,
}) => {
  const [picksCount, setPicksCount] = React.useState<number | null>(null);
  const [showVideo, setShowVideo] = React.useState(false);
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"));
  const details = matchPrediction;

  if (!open) return null;

  return (
    <Dialog
      key={matchPrediction?.match?.id}
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      fullScreen={isMobile}
      TransitionComponent={Slide}
      TransitionProps={{ direction: "up" } as TransitionProps}
      PaperProps={{
        sx: {
          width: { xs: "100%", sm: "100%" },
          margin: { xs: 0, sm: 2 },
          maxHeight: { xs: "100%", sm: "calc(100% - 64px)" },
          borderRadius: isMobile ? 0 : 2,
          background: "rgba(15, 23, 42, 0.85)",
          backdropFilter: "blur(16px)",
          border: "1px solid rgba(255, 255, 255, 0.1)",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
        },
      }}
    >
      <DialogTitle sx={{ textAlign: "center", pb: 1, pt: 2 }}>
        <Typography component="span" variant="h6" fontWeight="bold">
          Detalles del Partido
        </Typography>
      </DialogTitle>

      <DialogContent sx={{ px: { xs: 1.5, sm: 3 }, pb: 3, overflowX: "hidden" }}>
        {!details ? (
          <Box p={3} textAlign="center">
            <Typography color="text.secondary">No hay datos disponibles.</Typography>
          </Box>
        ) : (
          <Box>
            <ScoreHeader details={details} />

            <Box mb={3}>
              <Box display="flex" alignItems="center" justifyContent="space-between" mb={1.5}>
                <Typography variant="subtitle1" fontWeight="bold" sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                  Picks Destacados
                </Typography>
                {picksCount !== null && picksCount > 0 && (
                  <Chip
                    label={`${picksCount} picks`}
                    size="small"
                    sx={{
                      fontWeight: "bold",
                      bgcolor: "rgba(255, 255, 255, 0.1)",
                      color: "rgba(255, 255, 255, 0.9)",
                      border: "1px solid rgba(255, 255, 255, 0.2)",
                    }}
                  />
                )}
              </Box>
              {details?.prediction?.suggested_picks && details.prediction.suggested_picks.length > 0 ? (
                <SuggestedPicksTab matchPrediction={details} onPicksCount={setPicksCount} />
              ) : (
                <Box py={4} textAlign="center">
                  <Typography variant="caption" color="text.secondary">
                    No hay picks disponibles para este partido.
                  </Typography>
                </Box>
              )}
            </Box>

            <Divider sx={{ mb: 2.5 }} />

            <StatsGrid details={details} />

            <ProjectedStats details={details} />

            {details.prediction.highlights_url && (
              <VideoHighlights
                url={details.prediction.highlights_url}
                showVideo={showVideo}
                onShowVideo={() => setShowVideo(true)}
              />
            )}

            <RecommendationBox details={details} />
          </Box>
        )}
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button
          onClick={onClose}
          variant="outlined"
          color="inherit"
          sx={{
            borderColor: "rgba(255, 255, 255, 0.2)",
            color: "rgba(255, 255, 255, 0.7)",
            "&:hover": {
              borderColor: "#3b82f6",
              color: "#3b82f6",
              background: "rgba(59, 130, 246, 0.1)",
            },
          }}
        >
          Cerrar
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default MatchDetailsModal;

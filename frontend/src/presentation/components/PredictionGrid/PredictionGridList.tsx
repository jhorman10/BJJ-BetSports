import React, { lazy, Suspense } from "react";
import { Box, Skeleton, Grow } from "@mui/material";
import Grid from "@mui/material/Grid";
import { MatchPrediction } from "../../../types";

const MatchCard = lazy(() => import("../MatchCard"));

// Skeleton component for loading states
const MatchCardSkeleton: React.FC = () => (
  <Box
    sx={{
      p: 3,
      borderRadius: 2,
      bgcolor: "rgba(30, 41, 59, 0.5)",
      border: "1px solid rgba(148, 163, 184, 0.1)",
    }}
  >
    <Skeleton variant="text" width="40%" height={20} sx={{ mb: 2 }} />
    <Skeleton variant="text" width="80%" height={28} sx={{ mb: 1 }} />
    <Skeleton
      variant="rectangular"
      height={60}
      sx={{ mb: 2, borderRadius: 1 }}
    />
    <Skeleton variant="text" width="100%" height={16} sx={{ mb: 1 }} />
    <Skeleton variant="text" width="100%" height={16} sx={{ mb: 1 }} />
    <Skeleton variant="text" width="100%" height={16} sx={{ mb: 2 }} />
    <Box display="flex" gap={1}>
      <Skeleton variant="rounded" width={80} height={24} />
      <Skeleton variant="rounded" width={80} height={24} />
    </Box>
  </Box>
);

interface PredictionGridListProps {
  predictions: MatchPrediction[];
  onMatchClick: (matchPrediction: MatchPrediction) => void;
  selectedMatchIds?: string[];
  loadingMatchIds?: Set<string>;
  onToggleMatchSelection?: (match: MatchPrediction) => void;
}

const PredictionGridList: React.FC<PredictionGridListProps> = ({
  predictions,
  onMatchClick,
  selectedMatchIds = [],
  loadingMatchIds = new Set(),
  onToggleMatchSelection,
}) => {
  return (
    <Grid container spacing={3}>
      {predictions.map((matchPrediction, index) => (
        <Grid size={{ xs: 12, sm: 6, lg: 4 }} key={matchPrediction.match.id}>
          <Grow
            in
            timeout={300 + index * 50}
            style={{ transformOrigin: "0 0 0" }}
          >
            <Box>
              <Suspense fallback={<MatchCardSkeleton />}>
                <MatchCard
                  matchPrediction={matchPrediction}
                  highlight={index === 0}
                  onClick={() => onMatchClick(matchPrediction)}
                  isSelected={selectedMatchIds.includes(
                    matchPrediction.match.id
                  )}
                  isLoading={loadingMatchIds.has(matchPrediction.match.id)}
                  onToggleSelection={() =>
                    onToggleMatchSelection &&
                    onToggleMatchSelection(matchPrediction)
                  }
                />
              </Suspense>
            </Box>
          </Grow>
        </Grid>
      ))}
    </Grid>
  );
};

export default PredictionGridList;
export { MatchCardSkeleton };

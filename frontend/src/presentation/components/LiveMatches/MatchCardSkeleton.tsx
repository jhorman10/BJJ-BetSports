import React from "react";
import {
  Box,
  Card,
  CardContent,
  Stack,
  Skeleton,
} from "@mui/material";

const MatchCardSkeleton: React.FC = () => (
  <Card
    sx={{
      background: "rgba(30, 41, 59, 0.4)",
      backdropFilter: "blur(5px)",
      border: "1px solid rgba(148, 163, 184, 0.1)",
      borderRadius: 2,
    }}
  >
    <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
      <Stack spacing={1.5}>
        <Box display="flex" justifyContent="space-between">
          <Skeleton variant="text" width={60} height={20} />
          <Skeleton variant="text" width={80} height={20} />
        </Box>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Skeleton variant="text" width={100} height={24} />
          <Skeleton
            variant="rectangular"
            width={60}
            height={30}
            sx={{ borderRadius: 1 }}
          />
          <Skeleton variant="text" width={100} height={24} />
        </Box>
        <Skeleton
          variant="rectangular"
          width="100%"
          height={8}
          sx={{ borderRadius: 1 }}
        />
      </Stack>
    </CardContent>
  </Card>
);

export default MatchCardSkeleton;

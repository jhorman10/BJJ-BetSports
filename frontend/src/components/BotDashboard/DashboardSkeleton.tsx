import React from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Skeleton,
} from "@mui/material";

const DashboardSkeleton: React.FC = () => {
  return (
    <Box>
      {/* Header Skeleton */}
      <Box
        sx={{
          background:
            "linear-gradient(135deg, rgba(99, 102, 241, 0.1) 0%, rgba(16, 185, 129, 0.1) 100%)",
          borderRadius: 4,
          p: 4,
          mb: 4,
          border: "1px solid rgba(99, 102, 241, 0.2)",
          position: "relative",
          overflow: "hidden",
          "&::before": {
            content: '""',
            position: "absolute",
            top: 0,
            left: 0,
            right: 0,
            height: "3px",
            background: "linear-gradient(90deg, #6366f1, #10b981, #6366f1)",
            backgroundSize: "200% 100%",
            animation: "gradient 2s ease infinite",
          },
          "@keyframes gradient": {
            "0%": { backgroundPosition: "0% 50%" },
            "50%": { backgroundPosition: "100% 50%" },
            "100%": { backgroundPosition: "0% 50%" },
          },
        }}
      >
        <Box display="flex" alignItems="center" gap={3} flexWrap="wrap">
          <Skeleton
            variant="circular"
            width={56}
            height={56}
            sx={{ bgcolor: "rgba(255,255,255,0.1)" }}
          />
          <Box flex={1}>
            <Skeleton
              variant="text"
              width="60%"
              height={40}
              sx={{ bgcolor: "rgba(255,255,255,0.1)" }}
            />
            <Skeleton
              variant="text"
              width="40%"
              height={24}
              sx={{ bgcolor: "rgba(255,255,255,0.05)", mt: 1 }}
            />
          </Box>
          <Skeleton
            variant="rounded"
            width={200}
            height={40}
            sx={{ bgcolor: "rgba(255,255,255,0.1)" }}
          />
        </Box>
      </Box>

      {/* Stats Grid Skeleton */}
      <Grid container spacing={3} mb={4}>
        {[1, 2, 3, 4].map((i) => (
          <Grid item xs={12} md={3} key={i}>
            <Card
              sx={{
                height: "100%",
                background:
                  "linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)",
                backdropFilter: "blur(20px)",
                border: "1px solid rgba(148, 163, 184, 0.2)",
                borderRadius: 3,
                position: "relative",
                overflow: "hidden",
                "&::after": {
                  content: '""',
                  position: "absolute",
                  top: 0,
                  left: "-100%",
                  width: "100%",
                  height: "100%",
                  background:
                    "linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent)",
                  animation: "shimmer 2s infinite",
                },
                "@keyframes shimmer": {
                  "0%": { left: "-100%" },
                  "100%": { left: "100%" },
                },
              }}
            >
              <CardContent sx={{ p: 3 }}>
                <Box display="flex" justifyContent="space-between" mb={2}>
                  <Box flex={1}>
                    <Skeleton
                      variant="text"
                      width="60%"
                      sx={{ bgcolor: "rgba(255,255,255,0.1)" }}
                    />
                    <Skeleton
                      variant="text"
                      width="80%"
                      height={48}
                      sx={{ bgcolor: "rgba(255,255,255,0.15)", mt: 2 }}
                    />
                    <Skeleton
                      variant="text"
                      width="50%"
                      sx={{ bgcolor: "rgba(255,255,255,0.05)", mt: 1 }}
                    />
                  </Box>
                  <Skeleton
                    variant="rounded"
                    width={56}
                    height={56}
                    sx={{ bgcolor: "rgba(255,255,255,0.1)" }}
                  />
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Chart Skeleton */}
      <Card
        sx={{
          background:
            "linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)",
          backdropFilter: "blur(20px)",
          border: "1px solid rgba(99, 102, 241, 0.2)",
          borderRadius: 3,
          mb: 4,
        }}
      >
        <CardContent sx={{ p: 4 }}>
          <Skeleton
            variant="text"
            width="40%"
            height={32}
            sx={{ bgcolor: "rgba(255,255,255,0.1)", mb: 3 }}
          />
          <Skeleton
            variant="rectangular"
            width="100%"
            height={200}
            sx={{ bgcolor: "rgba(255,255,255,0.05)", borderRadius: 2 }}
          />
        </CardContent>
      </Card>

      {/* Table Skeleton */}
      <Box>
        <Skeleton
          variant="text"
          width="30%"
          height={32}
          sx={{ bgcolor: "rgba(255,255,255,0.1)", mb: 2 }}
        />
        <Skeleton
          variant="text"
          width="50%"
          height={24}
          sx={{ bgcolor: "rgba(255,255,255,0.05)", mb: 3 }}
        />
        <Card
          sx={{
            background:
              "linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.98) 100%)",
            backdropFilter: "blur(20px)",
            border: "1px solid rgba(148, 163, 184, 0.2)",
            borderRadius: 3,
          }}
        >
          <CardContent sx={{ p: 3 }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <Box key={i} mb={2}>
                <Skeleton
                  variant="rectangular"
                  width="100%"
                  height={60}
                  sx={{ bgcolor: "rgba(255,255,255,0.05)", borderRadius: 1 }}
                />
              </Box>
            ))}
          </CardContent>
        </Card>
      </Box>

      {/* Loading Text */}
      <Box
        sx={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 1000,
          pointerEvents: "none",
        }}
      >
        <Typography
          variant="h4"
          fontWeight={800}
          sx={{
            background: "linear-gradient(135deg, #6366f1 0%, #10b981 100%)",
            backgroundClip: "text",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
            animation: "pulse 2s ease-in-out infinite",
            "@keyframes pulse": {
              "0%, 100%": { opacity: 1 },
              "50%": { opacity: 0.5 },
            },
          }}
        >
          Cargando datos del modelo...
        </Typography>
      </Box>
    </Box>
  );
};

export default DashboardSkeleton;

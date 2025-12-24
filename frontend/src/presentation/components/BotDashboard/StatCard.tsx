import React from "react";
import { Box, Card, CardContent, Typography } from "@mui/material";

export interface StatCardProps {
  title: string;
  value: string;
  icon: React.ReactNode;
  color: string;
  subtitle?: string;
}

const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  icon,
  color,
  subtitle,
}) => (
  <Card
    sx={{
      height: "100%",
      bgcolor: "rgba(30, 41, 59, 0.6)",
      backdropFilter: "blur(10px)",
      border: "1px solid rgba(148, 163, 184, 0.1)",
      color: "white",
    }}
  >
    <CardContent>
      <Box
        display="flex"
        justifyContent="space-between"
        alignItems="flex-start"
      >
        <Box>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {title}
          </Typography>
          <Typography variant="h4" fontWeight={700} sx={{ color }}>
            {value}
          </Typography>
          {subtitle && (
            <Typography variant="caption" color="text.secondary">
              {subtitle}
            </Typography>
          )}
        </Box>
        <Box
          sx={{
            p: 1,
            borderRadius: 2,
            bgcolor: `${color}20`,
            color: color,
          }}
        >
          {icon}
        </Box>
      </Box>
    </CardContent>
  </Card>
);

export default StatCard;

import React from "react";
import {
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
} from "@mui/material";

interface MarketStat {
  market_type: string;
  market_label: string;
  total: number;
  won: number;
  lost: number;
  accuracy: number;
}

interface MarketStatsTableProps {
  stats: MarketStat[];
}

const MarketStatsTable: React.FC<MarketStatsTableProps> = ({ stats }) => (
  <Card
    sx={{
      bgcolor: "rgba(30, 41, 59, 0.6)",
      backdropFilter: "blur(10px)",
      border: "1px solid rgba(148, 163, 184, 0.1)",
    }}
  >
    <CardContent>
      <Typography variant="h6" fontWeight={700} color="white" gutterBottom>
        Porcentaje de Aciertos por Tipo
      </Typography>
      <Typography variant="body2" color="text.secondary" mb={2}>
        Rendimiento desglosado por cada tipo de mercado
      </Typography>
      <TableContainer component={Paper} sx={{ bgcolor: "transparent", overflowX: "auto" }}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell sx={{ color: "rgba(255,255,255,0.7)", fontWeight: 700 }}>
                Tipo de Mercado
              </TableCell>
              <TableCell align="center" sx={{ color: "rgba(255,255,255,0.7)", fontWeight: 700 }}>
                Total
              </TableCell>
              <TableCell align="center" sx={{ color: "rgba(255,255,255,0.7)", fontWeight: 700 }}>
                Ganados
              </TableCell>
              <TableCell align="center" sx={{ color: "rgba(255,255,255,0.7)", fontWeight: 700 }}>
                Perdidos
              </TableCell>
              <TableCell align="center" sx={{ color: "rgba(255,255,255,0.7)", fontWeight: 700 }}>
                % Aciertos
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {stats.map((stat) => (
              <TableRow key={stat.market_type}>
                <TableCell sx={{ color: "white" }}>{stat.market_label}</TableCell>
                <TableCell align="center" sx={{ color: "white" }}>{stat.total}</TableCell>
                <TableCell align="center" sx={{ color: "#22c55e" }}>{stat.won}</TableCell>
                <TableCell align="center" sx={{ color: "#ef4444" }}>{stat.lost}</TableCell>
                <TableCell align="center">
                  <Chip
                    label={`${stat.accuracy.toFixed(1)}%`}
                    size="small"
                    sx={{
                      bgcolor:
                        stat.accuracy >= 55
                          ? "rgba(34, 197, 94, 0.2)"
                          : stat.accuracy >= 45
                          ? "rgba(251, 191, 36, 0.2)"
                          : "rgba(239, 68, 68, 0.2)",
                      color:
                        stat.accuracy >= 55
                          ? "#22c55e"
                          : stat.accuracy >= 45
                          ? "#fbbf24"
                          : "#ef4444",
                      fontWeight: 700,
                    }}
                  />
                </TableCell>
              </TableRow>
            ))}
            {stats.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} align="center" sx={{ color: "text.secondary" }}>
                  No hay datos disponibles
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </CardContent>
  </Card>
);

export default MarketStatsTable;

import React from "react";
import { Tabs, Tab } from "@mui/material";

interface CategoryTabsProps {
  activeTab: string;
  categoryCounts: Record<string, number>;
  onTabChange: (event: React.SyntheticEvent, newValue: string) => void;
}

const CategoryTabs: React.FC<CategoryTabsProps> = ({
  activeTab,
  categoryCounts,
  onTabChange,
}) => (
  <Tabs
    value={activeTab || false}
    onChange={onTabChange}
    variant="scrollable"
    scrollButtons="auto"
    textColor="secondary"
    indicatorColor="secondary"
    sx={{
      mb: 2,
      minHeight: 36,
      ml: 0,
      pl: 0,
      width: "100%",
      "& .MuiTabs-root": { ml: 0, pl: 0 },
      "& .MuiTabs-scroller": { ml: 0, pl: 0 },
      "& .MuiTabs-scrollButtons.Mui-disabled": { width: 0, display: "none" },
      "& .MuiTabs-flexContainer": { justifyContent: "flex-start" },
      "& .MuiTab-root": {
        minHeight: 36,
        minWidth: "auto",
        px: 1.5,
        fontSize: "0.75rem",
        fontWeight: 600,
        color: "rgba(255,255,255,0.6)",
        textTransform: "none",
        ml: 0,
        "&:first-of-type": { pl: 0, ml: 0 },
        "&.Mui-selected": { color: "#10b981" },
      },
      "& .MuiTabs-indicator": { backgroundColor: "#10b981" },
    }}
  >
    {categoryCounts.TOP_ML > 0 && (
      <Tab value="TOP_ML" label="🔥 Top ML" sx={{ color: "#fbbf24 !important" }} />
    )}
    {categoryCounts.GOALS > 0 && <Tab value="GOALS" label="Goles" />}
    {categoryCounts.CORNERS > 0 && <Tab value="CORNERS" label="Córners" />}
    {categoryCounts.CARDS > 0 && <Tab value="CARDS" label="Tarjetas" />}
    {categoryCounts.BTTS > 0 && <Tab value="BTTS" label="Ambos Marcan" />}
    {categoryCounts.WINNER > 0 && <Tab value="WINNER" label="Ganador" />}
    {categoryCounts.DOUBLE_CHANCE > 0 && <Tab value="DOUBLE_CHANCE" label="Doble Oportunidad" />}
    {categoryCounts.HANDICAPS > 0 && <Tab value="HANDICAPS" label="Hándicaps" />}
  </Tabs>
);

export default CategoryTabs;

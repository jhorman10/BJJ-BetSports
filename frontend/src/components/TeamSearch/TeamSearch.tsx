import React from "react";
import { TextField, InputAdornment } from "@mui/material";
import { Search } from "@mui/icons-material";

interface TeamSearchProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

const TeamSearch: React.FC<TeamSearchProps> = ({
  searchQuery,
  onSearchChange,
}) => {
  return (
    <TextField
      fullWidth
      variant="outlined"
      placeholder="Buscar equipo por nombre..."
      value={searchQuery}
      onChange={(e) => onSearchChange(e.target.value)}
      InputProps={{
        startAdornment: (
          <InputAdornment position="start">
            <Search color="action" />
          </InputAdornment>
        ),
      }}
      size="small"
      sx={{
        maxWidth: 500,
        margin: "0 auto",
        display: "flex",
        backgroundColor: "rgba(30, 41, 59, 0.6)",
        backdropFilter: "blur(10px)",
        borderRadius: 2,
        "& .MuiOutlinedInput-root": {
          "& fieldset": {
            borderColor: "rgba(148, 163, 184, 0.2)",
          },
          "&:hover fieldset": {
            borderColor: "rgba(99, 102, 241, 0.5)",
          },
          "&.Mui-focused fieldset": {
            borderColor: "#6366f1",
          },
        },
      }}
    />
  );
};

export default TeamSearch;

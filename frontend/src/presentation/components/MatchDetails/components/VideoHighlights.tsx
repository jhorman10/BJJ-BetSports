import React from "react";
import { Box, Typography } from "@mui/material";
import { PlayArrow } from "@mui/icons-material";

interface VideoHighlightsProps {
  url: string;
  showVideo: boolean;
  onShowVideo: () => void;
}

export const VideoHighlights: React.FC<VideoHighlightsProps> = ({ url, showVideo, onShowVideo }) => (
  <Box mb={3}>
    <Typography variant="subtitle1" fontWeight="bold" gutterBottom>
      Video Highlights
    </Typography>
    <Box
      sx={{
        position: "relative",
        paddingBottom: "56.25%",
        height: 0,
        overflow: "hidden",
        borderRadius: 2,
        bgcolor: "black",
      }}
    >
      {!showVideo ? (
        <Box
          onClick={onShowVideo}
          sx={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            background: "linear-gradient(rgba(0,0,0,0.3), rgba(0,0,0,0.7))",
            "&:hover .play-icon": { transform: "scale(1.2)", color: "#3b82f6" },
          }}
        >
          <Box
            className="play-icon"
            sx={{
              width: 64,
              height: 64,
              borderRadius: "50%",
              bgcolor: "rgba(255,255,255,0.1)",
              backdropFilter: "blur(4px)",
              border: "2px solid rgba(255,255,255,0.5)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.3s ease",
            }}
          >
            <PlayArrow sx={{ fontSize: 40, color: "white", ml: 0.5 }} />
          </Box>
          <Typography
            variant="subtitle2"
            sx={{
              position: "absolute",
              bottom: 16,
              color: "white",
              fontWeight: 600,
              textShadow: "0 2px 4px rgba(0,0,0,0.8)",
            }}
          >
            Ver Highlights
          </Typography>
        </Box>
      ) : (
        <iframe
          src={`${url}?autoplay=1`}
          frameBorder="0"
          width="100%"
          height="100%"
          allowFullScreen
          allow="autoplay; encrypted-media"
          title="Match Highlights"
          style={{ position: "absolute", top: 0, left: 0 }}
        />
      )}
    </Box>
  </Box>
);

import { useState, useEffect } from "react";

// Cache to store extracted colors and avoid re-processing
const colorCache: Record<string, string> = {};

/**
 * Extracts the dominant color from an image URL.
 * Prioritizes high saturation pixels to find the "brand" color.
 */
export const useImageColor = (imageUrl: string | undefined): string | null => {
  const [color, setColor] = useState<string | null>(() => {
    if (imageUrl && colorCache[imageUrl]) {
      return colorCache[imageUrl];
    }
    return null;
  });

  useEffect(() => {
    if (!imageUrl || colorCache[imageUrl]) return;

    const img = new Image();
    img.crossOrigin = "Anonymous";
    img.src = imageUrl;

    img.onload = () => {
      try {
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        // Resize for performance
        canvas.width = 50;
        canvas.height = 50;
        ctx.drawImage(img, 0, 0, 50, 50);

        const imageData = ctx.getImageData(0, 0, 50, 50);
        const data = imageData.data;
        let r = 0,
          g = 0,
          b = 0,
          count = 0;

        // Simple averaging but filtering out white/black/transparent
        for (let i = 0; i < data.length; i += 4) {
          const red = data[i];
          const green = data[i + 1];
          const blue = data[i + 2];
          const alpha = data[i + 3];

          // Ignore transparent
          if (alpha < 128) continue;

          // Ignore white-ish (high lightness)
          if (red > 240 && green > 240 && blue > 240) continue;

          // Ignore black-ish (low lightness)
          if (red < 15 && green < 15 && blue < 15) continue;

          r += red;
          g += green;
          b += blue;
          count++;
        }

        if (count > 0) {
          r = Math.floor(r / count);
          g = Math.floor(g / count);
          b = Math.floor(b / count);
          // Boost saturation slightly for the glow
          const finalColor = `rgb(${r}, ${g}, ${b})`;
          colorCache[imageUrl] = finalColor;
          setColor(finalColor);
        } else {
          // Fallback for purely black/white logos
          setColor("rgba(255, 255, 255, 0.3)");
        }
      } catch (e) {
        // CORS error likely or canvas tainted
        // Generate a deterministic color from the URL string
        console.warn(
          "CORS/Canvas error for image, generating fallback glow:",
          imageUrl,
          e
        );

        let hash = 0;
        for (let i = 0; i < imageUrl.length; i++) {
          hash = imageUrl.charCodeAt(i) + ((hash << 5) - hash);
        }

        // Use HSL to ensure vibrant colors (high saturation/lightness)
        const h = Math.abs(hash % 360);
        const s = 80; // High saturation
        const l = 60; // Medium-high lightness for glow

        const fallbackColor = `hsl(${h}, ${s}%, ${l}%)`;
        colorCache[imageUrl] = fallbackColor;
        setColor(fallbackColor);
      }
    };
  }, [imageUrl]);

  return color;
};

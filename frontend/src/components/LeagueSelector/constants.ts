// Country flag emojis and Spanish names
export const COUNTRY_DATA: Record<string, { flag: string; name: string }> = {
  England: { flag: "🏴󠁧󠁢󠁥󠁮󠁧󠁿", name: "Inglaterra" },
  Spain: { flag: "🇪🇸", name: "España" },
  Germany: { flag: "🇩🇪", name: "Alemania" },
  Italy: { flag: "🇮🇹", name: "Italia" },
  France: { flag: "🇫🇷", name: "Francia" },
  Netherlands: { flag: "🇳🇱", name: "Países Bajos" },
  Belgium: { flag: "🇧🇪", name: "Bélgica" },
  Portugal: { flag: "🇵🇹", name: "Portugal" },
  Turkey: { flag: "🇹🇷", name: "Turquía" },
  Greece: { flag: "🇬🇷", name: "Grecia" },
  Scotland: { flag: "🏴󠁧󠁢󠁳󠁣󠁴󠁿", name: "Escocia" },
  International: { flag: "🌎", name: "Torneos Internacionales" },
};

export const SELECT_STYLES = {
  height: 48,
  borderRadius: 2,
  backgroundColor: "rgba(15, 23, 42, 0.6)",
  backdropFilter: "blur(10px)",
  "& .MuiOutlinedInput-notchedOutline": {
    borderColor: "rgba(99, 102, 241, 0.3)",
    transition: "all 0.2s ease",
  },
  "&:hover .MuiOutlinedInput-notchedOutline": {
    borderColor: "rgba(99, 102, 241, 0.6)",
  },
  "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
    borderColor: "#6366f1",
    borderWidth: 2,
  },
  "& .MuiSelect-select": {
    display: "flex",
    alignItems: "center",
    gap: 1.5,
    py: 1.5,
  },
  "& .MuiSelect-icon": {
    color: "#6366f1",
    transition: "transform 0.2s ease",
  },
  "&.Mui-focused .MuiSelect-icon": {
    transform: "rotate(180deg)",
  },
};

export const MENU_PROPS = {
  PaperProps: {
    sx: {
      mt: 1,
      borderRadius: 2,
      backgroundColor: "rgba(30, 41, 59, 0.98)",
      backdropFilter: "blur(20px)",
      border: "1px solid rgba(99, 102, 241, 0.2)",
      boxShadow: "0 20px 40px rgba(0, 0, 0, 0.4)",
      maxHeight: 320,
      "& .MuiMenuItem-root": {
        borderRadius: 1,
        mx: 1,
        my: 0.5,
        transition: "all 0.15s ease",
        "&:hover": {
          backgroundColor: "rgba(99, 102, 241, 0.15)",
        },
        "&.Mui-selected": {
          backgroundColor: "rgba(99, 102, 241, 0.25)",
          "&:hover": {
            backgroundColor: "rgba(99, 102, 241, 0.3)",
          },
        },
      },
    },
  },
};

export const LEAGUE_TRANSLATIONS: Record<string, string> = {
  "Premier League": "Premier League",
  Bundesliga: "Bundesliga",
  "La Liga": "La Liga",
  "Serie A": "Serie A",
  "Ligue 1": "Ligue 1",
  Eredivisie: "Eredivisie",
  "Primeira Liga": "Primeira Liga",
  "UEFA Champions League": "UEFA Champions League",
  "UEFA Europa League": "UEFA Europa League",
  "World Cup": "Copa del Mundo",
  "European Championship": "Eurocopa",
  "Copa Libertadores": "Copa Libertadores",
  "Copa Sudamericana": "Copa Sudamericana",
  Friendlies: "Amistosos Internacionales",
  "Club Friendlies": "Amistosos de Clubes",
  Championship: "Championship (2ª Ing)",
  "Brasileirão Série A": "Brasileirão Série A",
};

export const getLeagueName = (name: string) => {
  if (!name) return "";
  return LEAGUE_TRANSLATIONS[name] || name;
};

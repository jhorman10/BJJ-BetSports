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
  International: { flag: "🌎", name: "Torneos Internacionales" },
  World: { flag: "🌍", name: "Mundial" },
  FIFA: { flag: "🌍", name: "Mundial" },
  Colombia: { flag: "🇨🇴", name: "Colombia" },
  Argentina: { flag: "🇦🇷", name: "Argentina" },
  Brazil: { flag: "🇧🇷", name: "Brasil" },
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
  disablePortal: true,
  anchorOrigin: { vertical: "bottom" as const, horizontal: "left" as const },
  transformOrigin: { vertical: "top" as const, horizontal: "left" as const },
  PaperProps: {
    sx: {
      mt: 1,
      borderRadius: 2,
      backgroundColor: "rgba(30, 41, 59, 0.98)",
      backdropFilter: "blur(20px)",
      border: "1px solid rgba(99, 102, 241, 0.2)",
      boxShadow: "0 20px 40px rgba(0, 0, 0, 0.4)",
      maxHeight: 320,
      maxWidth: "calc(100vw - 32px)",
      overflowX: "hidden" as const,
      "& .MuiMenuItem-root": {
        borderRadius: 1,
        mx: 1,
        my: 0.5,
        whiteSpace: "normal" as const,
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
  "Championship": "Championship (2ª Ing)",
  "League One": "League One (3ª Ing)",
  "League Two": "League Two (4ª Ing)",
  "FA Cup": "FA Cup",
  "Bundesliga": "Bundesliga",
  "2. Bundesliga": "2. Bundesliga",
  "La Liga": "La Liga",
  "Segunda Division": "Segunda División",
  "Copa del Rey": "Copa del Rey",
  "Serie A": "Serie A",
  "Serie B": "Serie B",
  "Ligue 1": "Ligue 1",
  "Ligue 2": "Ligue 2",
  "Eredivisie": "Eredivisie",
  "Eerste Divisie": "Eerste Divisie",
  "Primeira Liga": "Primeira Liga",
  "Liga Portugal 2": "Liga Portugal 2",
  "Jupiler Pro League": "Jupiler Pro League",
  "Challenger Pro League": "Challenger Pro League",
  "Champions League": "UEFA Champions League",
  "UEFA Champions League": "UEFA Champions League",
  "UEFA Europa League": "UEFA Europa League",
  "Europa League": "UEFA Europa League",
  "Conference League": "UEFA Conference League",
  "UEFA Conference League": "UEFA Conference League",
  "World Cup": "Copa del Mundo",
  "FIFA World Cup": "Copa del Mundo",
  "European Championship": "Eurocopa",
  "Copa Libertadores": "Copa Libertadores",
  "Copa Sudamericana": "Copa Sudamericana",
  "Friendlies": "Amistosos Internacionales",
  "Club Friendlies": "Amistosos de Clubes",
  "Brasileirão Série A": "Brasileirão Série A",
  "Primera A": "Liga BetPlay (Col)",
  "Liga Profesional Argentina": "Liga Profesional (Arg)",
  "Primera Division": "Primera División (Arg)",
};

export const getLeagueName = (name: string): string => {
  if (!name) return "";
  return LEAGUE_TRANSLATIONS[name] || name;
};

/**
 * Team Display Utilities
 *
 * Helper functions for displaying team information consistently across the app.
 */

import type { Team } from "../types";

/**
 * Default team logo to use when no logo_url is available
 * Inline SVG data URI of a shield/crest icon for reliability
 */
export const DEFAULT_TEAM_LOGO =
  "data:image/svg+xml," +
  encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 120" fill="none">
  <path d="M50 5 L90 20 L90 55 C90 85 50 115 50 115 C50 115 10 85 10 55 L10 20 Z" 
        fill="#374151" stroke="#6366f1" stroke-width="4"/>
  <circle cx="50" cy="55" r="20" fill="#6366f1" opacity="0.3"/>
  <circle cx="50" cy="55" r="12" fill="#6366f1"/>
</svg>
`);

/**
 * Get the team logo URL, returning default if not available
 */
export const getTeamLogo = (team: Team): string => {
  return team.logo_url || team.logo_url || DEFAULT_TEAM_LOGO;
};

/**
 * Common football club suffixes/prefixes to remove for cleaner display
 * Case insensitive regex to match whole words or commonly attached suffixes
 * Includes:
 * - English/Intl: FC, CF, AFC, SC, AC, AS, CD, UD
 * - German: SV, VfB, FSV, TSG, SpVgg, 1. (prefix)
 * - Eastern/Northern: FK, JK, SK, NK, HJK
 * - Belgium/Dutch: KV, K, RSC, KAA, KRC, KAS, USG
 * - Others: CA, CS, SD, RB (Red Bull - controversial but often removed for short names if generic)
 */
const TEAM_NAME_CLEANER_REGEX =
  /\b(FC|CF|AFC|SC|AC|AS|CD|UD|SV|VfB|FSV|TSG|FK|JK|SK|NK|CA|CS|SD|SpVgg|KV|K|RSC|KAA|KRC|KAS|USG|FCV|KVC)\b/gi;

/**
 * Cleans a team name by stripping common Generic suffixes/prefixes
 */
export const cleanTeamName = (name: string): string => {
  if (!name) return "";
  return name.replace(TEAM_NAME_CLEANER_REGEX, "").replace(/\s+/g, " ").trim();
};

/**
 * Get the shortest available team name and clean it up
 * Priority: short_name > name
 * Cleans: "Chelsea FC" -> "Chelsea", "Arsenal AFC" -> "Arsenal"
 */
export const getTeamDisplayName = (team: Team): string => {
  const baseName = team.short_name || team.name;
  return cleanTeamName(baseName);
};

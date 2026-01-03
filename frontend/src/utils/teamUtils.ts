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
 * Get the shortest available team name
 * Priority: short_name > name
 */
export const getTeamDisplayName = (team: Team): string => {
  return team.short_name || team.name;
};

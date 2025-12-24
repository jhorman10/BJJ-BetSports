/**
 * Search Utilities
 *
 * Unified search logic for the application.
 * Mirrors the backend logic in StatisticsService for consistency.
 *
 * Features:
 * - Accent insensitive (Atlético == atletico)
 * - Case insensitive
 * - Ignores common prefixes (FC, AC, Real, etc.)
 * - Hybrid matching (Raw + Normalized)
 */

// Must match backend: ["fc", "cf", "as", "sc", "ac", "real", "sporting", "club", "de", "le", "la"]
const IGNORED_TERMS = [
  "fc",
  "cf",
  "as",
  "sc",
  "ac",
  "real",
  "sporting",
  "club",
  "de",
  "le",
  "la",
];

/**
 * Normalizes a string for comparison:
 * 1. Remove accents
 * 2. Lowercase and trim
 * 3. Remove common football terms
 * 4. Remove spaces
 */
export const normalizeName = (name: string): string => {
  if (!name) return "";

  // 1. Remove accents (NFD normalization)
  // Decomposes combined chars (e.g., "é" -> "e" + "´") and removes the marks
  let cleaned = name.normalize("NFD").replace(/[\u0300-\u036f]/g, "");

  // 2. Lowercase and trim
  cleaned = cleaned.toLowerCase().trim();

  // 3. Remove common terms
  IGNORED_TERMS.forEach((term) => {
    // Remove isolated occurrences (start, end, or middle surrounded by spaces)
    if (cleaned.startsWith(`${term} `))
      cleaned = cleaned.substring(term.length + 1);
    if (cleaned.endsWith(` ${term}`))
      cleaned = cleaned.substring(0, cleaned.length - term.length - 1);
    cleaned = cleaned.replace(new RegExp(`\\b${term}\\b`, "g"), " ");
  });

  // 4. Remove all remaining spaces
  return cleaned.replace(/\s+/g, "");
};

/**
 * Determines if a candidate string matches the search query.
 * Implements a hybrid strategy for best UX.
 */
export const isSearchMatch = (query: string, candidate: string): boolean => {
  if (!query) return true;
  if (!candidate) return false;

  const qRaw = query.toLowerCase().trim();
  const cRaw = candidate.toLowerCase().trim();

  // 1. Fast path: Raw containment
  // Handles cases where user types "Real" and wants "Real Madrid" (which normalization might strip)
  if (cRaw.includes(qRaw)) return true;

  // 2. Normalized comparison
  const qNorm = normalizeName(query);
  const cNorm = normalizeName(candidate);

  // If normalization reduced query to empty (e.g. user typed "FC"), rely on raw match above
  if (!qNorm) return false;

  // Logic: Exact match OR Prefix match (2+ chars) OR Contains match (3+ chars)
  if (cNorm === qNorm) return true;
  if (qNorm.length >= 2 && cNorm.startsWith(qNorm)) return true;
  if (qNorm.length >= 3 && cNorm.includes(qNorm)) return true;

  return false;
};

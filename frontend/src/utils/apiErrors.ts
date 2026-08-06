/**
 * Classifies whether an error represents a network-level failure:
 * the backend is unreachable ("Network Error" / ERR_NETWORK) or the
 * request was aborted by a timeout (ECONNABORTED).
 */
export function isNetworkError(error: unknown): boolean {
  if (typeof error !== "object" || error === null) return false;
  const candidate = error as { message?: unknown; code?: unknown };
  return (
    candidate.message === "Network Error" ||
    candidate.code === "ERR_NETWORK" ||
    candidate.code === "ECONNABORTED"
  );
}

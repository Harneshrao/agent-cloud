/**
 * Client-side auth:
 * - Store the access token under `token` (primary) and `access_token` (back-compat).
 * - Optionally store `refresh_token` for rotation if backend supports it.
 */

const TOKEN_KEY = "token";
const ACCESS_TOKEN_KEY = "access_token"; // back-compat
const REFRESH_TOKEN_KEY = "refresh_token";

const DEFAULT_API = "http://127.0.0.1:8000";

export function getApiBase(): string {
  return process.env.NEXT_PUBLIC_API_URL || DEFAULT_API;
}

export function getApiBaseAlternate(): string | null {
  return null;
}

/** Single in-flight refresh promise so multiple 401s don't trigger parallel refreshes. */
let refreshingToken: Promise<string> | null = null;

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY) || localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setTokens(accessToken: string, refreshToken?: string | null): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(TOKEN_KEY, accessToken);
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  if (refreshToken != null) {
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }
}

export function clearTokens(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function isAuthenticated(): boolean {
  return !!getAccessToken();
}

/**
 * Exchange refresh_token for new access_token and refresh_token (rotation).
 * Uses a global lock so concurrent callers share one refresh request.
 * On failure: clears tokens and throws.
 */
export async function refreshAccessToken(): Promise<string> {
  if (refreshingToken) {
    return refreshingToken;
  }

  refreshingToken = (async (): Promise<string> => {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      clearTokens();
      throw new Error("No refresh token available");
    }

    const res = await fetch(`${getApiBase()}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      clearTokens();
      throw new Error("Token refresh failed");
    }

    const data = (await res.json()) as { access_token?: string; refresh_token?: string };
    const newAccess = data.access_token;
    const newRefresh = data.refresh_token ?? null;
    if (!newAccess) {
      clearTokens();
      throw new Error("Token refresh failed");
    }
    setTokens(newAccess, newRefresh);
    return newAccess;
  })();

  try {
    return await refreshingToken;
  } finally {
    refreshingToken = null;
  }
}

const REFRESH_INTERVAL_MS = 10 * 60 * 1000; // 10 minutes

/** Call once after login to proactively refresh the access token every 10 minutes. */
export function startTokenRefreshTimer(): void {
  if (typeof window === "undefined") return;
  setInterval(() => {
    if (!getRefreshToken()) return;
    refreshAccessToken().catch(() => {});
  }, REFRESH_INTERVAL_MS);
}

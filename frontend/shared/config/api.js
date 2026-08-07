/**
 * Single source of truth for the backend's address.
 *
 * `VITE_API_URL` is read at BUILD time, not run time — Vite inlines the value
 * into the bundle. Changing it after a deploy has no effect; it must be set in
 * the build environment (Vercel project settings, or the `VITE_API_URL`
 * build-arg the frontend Dockerfile already accepts).
 *
 * The dev fallback is only correct on a machine that is itself running the
 * backend. In a deployed bundle `localhost` means the *visitor's* computer, so
 * if VITE_API_URL is missing at build time every request fails at runtime even
 * though the build succeeded.
 */

// Stripped so callers can write `${API_BASE_URL}/users/me` without risking a
// double slash when the configured value has a trailing one.
const stripTrailingSlash = (url) => url.replace(/\/+$/, '');

export const API_BASE_URL = stripTrailingSlash(
  import.meta.env.VITE_API_URL || 'http://localhost:8000'
);

export const LOGIN_URL = `${API_BASE_URL}/login/`;
export const REGISTER_URL = `${API_BASE_URL}/auth/register`;

/**
 * WebSocket origin, derived from API_BASE_URL rather than configured separately.
 *
 * Deriving the scheme (https -> wss, http -> ws) rules out a failure mode that
 * is tedious to diagnose: browsers silently refuse a plaintext `ws://` socket
 * opened from an HTTPS page (mixed content). Because the mapping happens here,
 * an HTTPS API can never be paired with an insecure socket URL by accident.
 *
 * VITE_WS_URL still takes precedence, for the case where sockets are served
 * from a different host than the REST API.
 */
export const WS_BASE_URL = stripTrailingSlash(
  import.meta.env.VITE_WS_URL ||
    API_BASE_URL.replace(/^http(s?):\/\//, 'ws$1://')
);

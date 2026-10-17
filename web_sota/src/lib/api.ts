// API base URL for backend calls.
//
// Same-origin ("") by default: the vite dev server proxies /api, /health and
// /mcp to the backend on :10913, so browser tabs work from any hostname
// (localhost, LAN name, Tailscale MagicDNS, goliath) without CORS failures.
// Absolute backend URL only inside the Tauri WebView, where no vite proxy
// exists (fleet CORS rule: absolute URLs must sit behind a Tauri gate).
const isTauri =
  typeof window !== "undefined" &&
  ("__TAURI__" in window || "__TAURI_INTERNALS__" in window);

export const API_BASE = isTauri ? "http://127.0.0.1:10913" : "";

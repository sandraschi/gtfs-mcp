import { useCallback, useEffect, useState } from "react";

const ZOOM_LEVELS = [0.8, 1.0, 1.25, 1.5, 2.0, 3.0];

export function useZoom() {
  const [zoomIndex, setZoomIndex] = useState(() => {
    try {
      const saved = localStorage.getItem("tauri-zoom");
      return saved ? Math.max(0, ZOOM_LEVELS.indexOf(parseFloat(saved))) : 0;
    } catch {
      return 0;
    }
  });

  const applyZoom = useCallback(async (level: number) => {
    localStorage.setItem("tauri-zoom", String(level));
    try {
      // Tauri 2.11+: zoom lives on the Webview handle.
      const webview = await import("@tauri-apps/api/webview");
      await webview.getCurrentWebview().setZoom(level);
      return;
    } catch {
      // dev browser - fall through to CSS zoom
    }
    // CSS zoom fallback for the dev browser (Chrome/Edge/Safari)
    (
      document.documentElement.style as CSSStyleDeclaration & {
        zoom?: string;
      }
    ).zoom = String(level);
  }, []);

  useEffect(() => {
    const handler = (e: WheelEvent) => {
      if (!e.ctrlKey) return;
      e.preventDefault();
      setZoomIndex((prev) => {
        const next =
          e.deltaY < 0
            ? Math.min(prev + 1, ZOOM_LEVELS.length - 1)
            : Math.max(prev - 1, 0);
        if (next !== prev) applyZoom(ZOOM_LEVELS[next]);
        return next;
      });
    };
    const resetHandler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "0") {
        e.preventDefault();
        setZoomIndex(0);
        applyZoom(ZOOM_LEVELS[0]);
      }
    };
    window.addEventListener("wheel", handler, { passive: false });
    window.addEventListener("keydown", resetHandler);
    const saved = localStorage.getItem("tauri-zoom");
    if (saved) applyZoom(parseFloat(saved));
    return () => {
      window.removeEventListener("wheel", handler);
      window.removeEventListener("keydown", resetHandler);
    };
  }, [applyZoom]);

  return { zoomLevel: ZOOM_LEVELS[zoomIndex] };
}

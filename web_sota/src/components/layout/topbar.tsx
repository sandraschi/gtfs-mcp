"use client";

import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { ExternalLink, HelpCircle, LayoutGrid } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { APPS_CATALOG } from "@/common/apps-catalog";
import { API_BASE } from "@/lib/api";

export function Topbar() {
  const [backendOk, setBackendOk] = useState<boolean | null>(null);

  const refresh = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/api/health`, {
        signal: AbortSignal.timeout(4000),
      });
      setBackendOk(r.ok);
    } catch {
      setBackendOk(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, 10_000);
    return () => clearInterval(interval);
  }, [refresh]);

  useEffect(() => {
    let unlisten: (() => void) | undefined;
    (async () => {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        unlisten = await listen<string>("backend-status", (event) => {
          if (event.payload === "ready") refresh();
          else if (
            typeof event.payload === "string" &&
            event.payload.startsWith("error:")
          ) {
            setBackendOk(false);
          }
        });
      } catch {
        // Not inside Tauri - HTTP polling handles it
      }
    })();
    return () => {
      if (unlisten) unlisten();
    };
  }, [refresh]);

  const dotClass =
    backendOk === null
      ? "bg-slate-500"
      : backendOk
        ? "bg-emerald-500"
        : "bg-red-500";
  const label =
    backendOk === null
      ? "Connecting..."
      : backendOk
        ? "System Online"
        : "Offline";

  return (
    <header className="flex h-14 items-center justify-between border-b border-slate-800 bg-slate-950/50 px-6 backdrop-blur-xl">
      <div className="flex items-center gap-4">
        <h1 className="text-sm font-medium text-slate-300">
          Navigation / <span className="text-slate-100">Control Center</span>
        </h1>
      </div>

      <div className="flex items-center gap-2">
        {/* Live System Status Indicator */}
        <div
          data-testid="topbar-backend-dot"
          className={`mr-4 flex items-center gap-2 rounded-full px-3 py-1 text-xs border ${
            backendOk === null
              ? "bg-slate-900/60 border-slate-700 text-slate-300"
              : backendOk
                ? "bg-emerald-500/10 border-emerald-500/20 text-emerald-500"
                : "bg-red-500/10 border-red-500/20 text-red-500"
          }`}
        >
          <span className="relative flex h-2 w-2">
            {backendOk === true && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            )}
            <span
              className={`relative inline-flex h-2 w-2 rounded-full ${dotClass}`}
            />
          </span>
          {label}
        </div>

        {/* Global Apps Navigation */}
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button
              type="button"
              className="flex items-center gap-2 rounded-md border border-slate-800 bg-slate-900/50 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-700"
            >
              <LayoutGrid className="h-4 w-4" />
              Apps
            </button>
          </DropdownMenu.Trigger>

          <DropdownMenu.Portal>
            <DropdownMenu.Content
              className="z-50 min-w-[220px] animate-in fade-in zoom-in-95 data-[side=bottom]:slide-in-from-top-2 rounded-md border border-slate-800 bg-slate-950 p-1 shadow-xl"
              sideOffset={5}
              align="end"
            >
              <DropdownMenu.Label className="px-2 py-1.5 text-xs font-semibold text-slate-500">
                Switch Application
              </DropdownMenu.Label>

              <div className="h-px bg-slate-800 my-1" />

              {APPS_CATALOG.map((app) => (
                <DropdownMenu.Item key={app.id} asChild>
                  <a
                    href={app.url}
                    className="flex w-full select-none items-center rounded-sm px-2 py-1.5 text-sm text-slate-300 hover:bg-slate-800 hover:text-white focus:bg-slate-800 focus:text-white outline-none cursor-pointer"
                  >
                    <app.icon className="mr-2 h-4 w-4 text-slate-400" />
                    <span>{app.label}</span>
                    <ExternalLink className="ml-auto h-3 w-3 opacity-50" />
                  </a>
                </DropdownMenu.Item>
              ))}
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>

        <button
          type="button"
          className="flex h-8 w-8 items-center justify-center rounded-md border border-slate-800 bg-slate-900/50 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
          title="Help"
        >
          <HelpCircle className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
}

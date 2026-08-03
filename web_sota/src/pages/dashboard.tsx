import { Activity, Clock, Cpu, Database, Layers, Shield } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";

interface Health {
  status: string;
  server: string;
  version: string;
  uptime_seconds: number;
  tool_count: number;
  providers?: Record<string, unknown>;
}

interface LogEntry {
  id?: string;
  timestamp: string;
  level: string;
  kind: string;
  message: string;
}

const BACKOFF_MS = [1000, 2000, 4000, 8000, 16000];

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export function Dashboard() {
  const [health, setHealth] = useState<Health | null>(null);
  const [backendOk, setBackendOk] = useState<boolean | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [pollIndex, setPollIndex] = useState(0);

  const refresh = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/api/health`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = (await r.json()) as Health;
      setHealth(data);
      setBackendOk(true);
      setPollIndex(0);
    } catch {
      setBackendOk(false);
      setPollIndex((i) => Math.min(i + 1, BACKOFF_MS.length - 1));
    }
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, BACKOFF_MS[pollIndex]);
    return () => clearInterval(interval);
  }, [refresh, pollIndex]);

  useEffect(() => {
    fetch(`${API_BASE}/api/logs?limit=12`)
      .then((r) => r.json())
      .then((d) => setLogs(d.entries ?? []))
      .catch(() => setLogs([]));
  }, []);

  const statusText =
    backendOk === null ? "Connecting..." : backendOk ? "Online" : "Offline";
  const statusColor =
    backendOk === null
      ? "text-slate-300"
      : backendOk
        ? "text-emerald-500"
        : "text-red-500";
  const dotColor =
    backendOk === null
      ? "bg-slate-500"
      : backendOk
        ? "bg-emerald-500"
        : "bg-red-500";

  return (
    <div data-testid="dashboard" className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">
            Gtfs MCP Dashboard
          </h2>
          <p className="text-sm text-slate-300">
            GTFS schedule and real-time transit data server.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-full bg-slate-900/60 border border-slate-800 px-3 py-1.5">
          <span
            className={`relative flex h-2 w-2 ${dotColor} rounded-full`}
            data-testid="backend-dot"
          >
            {backendOk === true && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            )}
          </span>
          <span className={`text-sm font-medium ${statusColor}`}>
            {statusText}
          </span>
          {health && (
            <span className="text-xs text-slate-400">
              v{health.version} - {health.tool_count} tools
            </span>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">
              Server
            </CardTitle>
            <Shield className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div
              className="text-2xl font-bold text-white"
              data-testid="kpi-server"
            >
              {health?.server ?? "-"}
            </div>
            <p className="text-sm text-slate-300">{statusText}</p>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">
              Registered Tools
            </CardTitle>
            <Cpu className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div
              className="text-2xl font-bold text-white"
              data-testid="kpi-tools"
            >
              {health?.tool_count ?? "-"}
            </div>
            <p className="text-sm text-slate-300">MCP tools available</p>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">
              Uptime
            </CardTitle>
            <Clock className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div
              className="text-2xl font-bold text-white"
              data-testid="kpi-uptime"
            >
              {health ? formatUptime(health.uptime_seconds) : "-"}
            </div>
            <p className="text-sm text-slate-300">since last restart</p>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">
              Feed Manager
            </CardTitle>
            <Database className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div
              className="text-2xl font-bold text-white"
              data-testid="kpi-feed-manager"
            >
              {health?.providers?.feed_manager ? "Active" : "Idle"}
            </div>
            <p className="text-sm text-slate-300">GTFS feed backing store</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        <Card className="col-span-4 border-slate-800 bg-slate-950/50">
          <CardHeader>
            <CardTitle className="text-white">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[200px] font-mono text-xs p-4 overflow-y-auto border border-slate-800 rounded-md bg-slate-900/50 text-slate-300 space-y-1">
              {logs.length === 0 && (
                <p className="text-slate-400">
                  No log entries yet. Open the Logging page to inspect the ring
                  buffer.
                </p>
              )}
              {logs.map((entry, i) => (
                <p key={entry.id ?? `log-${i}`}>
                  <span className="text-blue-400">[{entry.timestamp}]</span>{" "}
                  <span className="text-slate-500">{entry.level}</span>{" "}
                  {entry.message}
                </p>
              ))}
            </div>
          </CardContent>
        </Card>
        <Card className="col-span-3 border-slate-800 bg-slate-950/50">
          <CardHeader>
            <CardTitle className="text-white">Quick Start</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center">
                <Layers className="h-4 w-4 text-slate-300 mr-2" />
                <div className="ml-2 space-y-1">
                  <p className="text-sm font-medium leading-none text-white">
                    Add a GTFS feed
                  </p>
                  <p className="text-sm text-slate-300">
                    Use <code className="text-blue-400">add_feed</code> or POST
                    /v1/feeds with a feed zip URL.
                  </p>
                </div>
              </div>
              <div className="flex items-center">
                <Activity className="h-4 w-4 text-emerald-500 mr-2" />
                <div className="ml-2 space-y-1">
                  <p className="text-sm font-medium leading-none text-white">
                    Query stops
                  </p>
                  <p className="text-sm text-slate-300">
                    <code className="text-blue-400">find_stops</code> and{" "}
                    <code className="text-blue-400">get_departures</code> cover
                    schedule lookups.
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

import { Cpu, Database, Server, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { API_BASE } from "@/lib/api";

interface Health {
  status: string;
  server: string;
  version: string;
  uptime_seconds: number;
  tool_count: number;
  providers?: Record<string, unknown>;
}

function LLMSettings() {
  const [providers, setProviders] = useState<
    Record<string, { name: string }[]>
  >({});
  const [selectedProvider, setSelectedProvider] = useState("ollama");
  const [selectedModel, setSelectedModel] = useState("");
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    "loading",
  );

  useEffect(() => {
    fetch(`${API_BASE}/api/llm/providers`)
      .then((r) => r.json())
      .then((d) => {
        setProviders(d);
        const savedP = localStorage.getItem("llm_provider") || "ollama";
        const savedM = localStorage.getItem("llm_model") || "";
        setSelectedProvider(savedP);
        const models = d[savedP === "ollama" ? "ollama" : "lm_studio"] || [];
        setSelectedModel(
          savedM && models.some((m: { name: string }) => m.name === savedM)
            ? savedM
            : models[0]?.name || "",
        );
        setStatus(models.length > 0 ? "ready" : "error");
      })
      .catch(() => {
        setProviders({});
        setSelectedModel("");
        setStatus("error");
      });
  }, []);

  const save = (p: string, m: string) => {
    localStorage.setItem("llm_provider", p);
    localStorage.setItem("llm_model", m);
  };
  const models =
    providers[selectedProvider === "ollama" ? "ollama" : "lm_studio"] || [];
  const detected = (providers.detected as unknown as string[]) ?? [];

  return (
    <Card className="border-slate-800 bg-slate-950/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-white">
          <Cpu className="h-4 w-4 text-blue-400" /> Local LLM
        </CardTitle>
        <CardDescription className="text-slate-400">
          Chat backend. Probes Ollama (11434) and LM Studio (1234) via the
          server.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center gap-2 text-sm">
          <span
            className={`h-2 w-2 rounded-full ${
              status === "ready"
                ? "bg-emerald-400"
                : status === "error"
                  ? "bg-red-400"
                  : "bg-amber-400 animate-pulse"
            }`}
          />
          <span className="text-slate-300">
            {status === "ready"
              ? `Detected: ${(detected ?? []).join(", ") || "none"}`
              : status === "error"
                ? "No local LLM detected - start Ollama or LM Studio"
                : "Probing..."}
          </span>
        </div>
        <select
          data-testid="llm-provider-select"
          className="h-9 w-full rounded-md border border-zinc-600 bg-zinc-800 px-3 text-sm text-zinc-100"
          value={selectedProvider}
          onChange={(e) => {
            setSelectedProvider(e.target.value);
            save(e.target.value, "");
          }}
        >
          <option value="ollama">Ollama</option>
          <option value="lm_studio">LM Studio</option>
        </select>
        <select
          data-testid="llm-model-select"
          className="h-9 w-full rounded-md border border-zinc-600 bg-zinc-800 px-3 text-sm text-zinc-100"
          value={selectedModel}
          onChange={(e) => {
            setSelectedModel(e.target.value);
            save(selectedProvider, e.target.value);
          }}
        >
          {models.length === 0 && <option value="">No models detected</option>}
          {models.map((m) => (
            <option key={m.name} value={m.name}>
              {m.name}
            </option>
          ))}
        </select>
        <p className="text-xs text-slate-400">
          Selection persists in browser storage (llm_provider / llm_model) and
          drives the Chat page.
        </p>
      </CardContent>
    </Card>
  );
}

function BackendHealth() {
  const [health, setHealth] = useState<Health | null>(null);
  const [ok, setOk] = useState<boolean | null>(null);

  const refresh = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/api/health`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setHealth((await r.json()) as Health);
      setOk(true);
    } catch {
      setOk(false);
    }
  }, []);

  useEffect(() => {
    refresh();
    const iv = setInterval(refresh, 10000);
    return () => clearInterval(iv);
  }, [refresh]);

  return (
    <Card className="border-slate-800 bg-slate-950/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-white">
          <Server className="h-4 w-4 text-emerald-500" /> Backend
        </CardTitle>
        <CardDescription className="text-slate-400">
          Live status of the GTFS MCP backend on port 10913.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <div className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full ${
              ok === null
                ? "bg-amber-400"
                : ok
                  ? "bg-emerald-400"
                  : "bg-red-400"
            }`}
          />
          <span className="text-slate-200" data-testid="backend-health-text">
            {ok === null
              ? "Connecting..."
              : ok
                ? `${health?.server} v${health?.version} - online`
                : "Offline"}
          </span>
        </div>
        {health && (
          <>
            <p className="text-slate-300">
              Tools:{" "}
              <span data-testid="settings-tool-count">{health.tool_count}</span>
            </p>
            <p className="text-slate-300">
              Uptime: {Math.floor(health.uptime_seconds / 60)} min
            </p>
            <p className="text-slate-300">
              Feed manager: {health.providers?.feed_manager ? "active" : "idle"}
            </p>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function FeedSummary() {
  const [count, setCount] = useState<number | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/v1/feeds`)
      .then((r) => r.json())
      .then((d: unknown[]) => setCount(d.length))
      .catch(() => setCount(null));
  }, []);

  return (
    <Card className="border-slate-800 bg-slate-950/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-white">
          <Database className="h-4 w-4 text-blue-400" /> Feeds
        </CardTitle>
        <CardDescription className="text-slate-400">
          Registered GTFS feeds on this server.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-bold text-white">
          {count === null ? "-" : count}
        </p>
        <p className="text-sm text-slate-300">
          {count === null
            ? "Could not reach the feeds endpoint."
            : count === 0
              ? "No feeds yet - add one on the Feeds page."
              : "feeds registered"}
        </p>
      </CardContent>
    </Card>
  );
}

function SecurityNote() {
  return (
    <Card className="border-slate-800 bg-slate-950/50">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-white">
          <ShieldCheck className="h-4 w-4 text-emerald-500" /> Security
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm text-slate-300">
        <p>
          API keys are read from configuration (.env at the repo root or
          app-data for the desktop build) - never from this page or chat.
        </p>
        <p>
          The installer bundles .env.example only; your personal keys never ship
          inside a build.
        </p>
      </CardContent>
    </Card>
  );
}

export function Settings() {
  return (
    <div data-testid="settings-page" className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">
          Settings
        </h2>
        <p className="text-sm text-slate-300">
          Backend health, local LLM integration, and feed status.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <BackendHealth />
        <FeedSummary />
      </div>
      <LLMSettings />
      <SecurityNote />
    </div>
  );
}

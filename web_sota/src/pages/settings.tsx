import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import {
  Check,
  ChevronDown,
  Cpu,
  Database,
  Server,
  ShieldCheck,
} from "lucide-react";
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

interface PickerOption {
  value: string;
  label: string;
}

/** Theme-controlled dropdown (Radix menu, not a native <select>).
 *
 * Native select popups are drawn by the browser/OS and ignore page CSS,
 * which produced black-on-black option lists. This renders the menu as
 * regular DOM in our palette, so it cannot go unreadable.
 */
function Picker({
  testid,
  value,
  placeholder,
  options,
  onPick,
}: {
  testid: string;
  value: string;
  placeholder: string;
  options: PickerOption[];
  onPick: (value: string) => void;
}) {
  const current = options.find((o) => o.value === value);
  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          data-testid={testid}
          className="flex h-9 w-full items-center justify-between gap-2 rounded-md border border-zinc-600 bg-zinc-800 px-3 text-sm text-zinc-100 hover:bg-zinc-700"
        >
          <span className="truncate">
            {current ? current.label : placeholder}
          </span>
          <ChevronDown className="h-4 w-4 shrink-0 text-zinc-400" />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          className="z-50 rounded-md border border-slate-700 bg-slate-950 p-1 shadow-xl"
          style={{ minWidth: "var(--radix-dropdown-menu-trigger-width)" }}
          sideOffset={4}
        >
          {options.length === 0 && (
            <p className="px-2 py-1.5 text-sm text-slate-400">{placeholder}</p>
          )}
          {options.map((o) => (
            <DropdownMenu.Item
              key={o.value}
              onSelect={() => onPick(o.value)}
              className="flex w-full cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm text-slate-200 outline-none hover:bg-slate-800 hover:text-white focus:bg-slate-800 focus:text-white"
            >
              <span className="flex-1 truncate">{o.label}</span>
              {o.value === value && (
                <Check className="ml-2 h-4 w-4 shrink-0 text-emerald-400" />
              )}
            </DropdownMenu.Item>
          ))}
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
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
        <Picker
          testid="llm-provider-select"
          value={selectedProvider}
          placeholder="Select provider"
          options={[
            { value: "ollama", label: "Ollama" },
            { value: "lm_studio", label: "LM Studio" },
          ]}
          onPick={(v) => {
            setSelectedProvider(v);
            save(v, "");
          }}
        />
        <Picker
          testid="llm-model-select"
          value={selectedModel}
          placeholder="No models detected"
          options={models.map((m) => ({ value: m.name, label: m.name }))}
          onPick={(v) => {
            setSelectedModel(v);
            save(selectedProvider, v);
          }}
        />
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

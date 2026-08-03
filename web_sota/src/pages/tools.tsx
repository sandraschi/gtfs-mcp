import { Wrench } from "lucide-react";
import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";

const TOOL_DESCRIPTIONS: Record<string, string> = {
  add_feed:
    "Register a GTFS feed from a zip URL (id, url, update interval, force refresh).",
  list_feeds: "List all registered feeds with their URLs and intervals.",
  find_stops:
    "Search stops by name, code, or id (case-insensitive substring, capped at 100).",
  get_departures:
    "Next departures for a stop, sorted by time, filtered by today's active service.",
  get_stop_info:
    "Full stop record: coordinates, location_type, zone, accessibility flags.",
  status: "Server status: registered feeds and service health.",
  shutdown: "Gracefully shut down the server (destructive).",
};

interface ToolEntry {
  name: string;
  description?: string;
}

export function Tools() {
  const [tools, setTools] = useState<ToolEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/diagnostics`)
      .then((r) => r.json())
      .then((d) => {
        setTools((d.tools ?? []) as ToolEntry[]);
        setLoading(false);
      })
      .catch((e) => {
        setError(e instanceof Error ? e.message : "Failed to load tools");
        setLoading(false);
      });
  }, []);

  return (
    <div data-testid="tools-page" className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Tools</h2>
        <p className="text-sm text-slate-300">
          The live MCP tool surface, fetched from the backend diagnostics.
        </p>
      </div>

      {loading && <p className="text-sm text-slate-400">Loading tools...</p>}
      {error && <p className="text-sm text-red-400">{error}</p>}

      <div className="grid gap-3 md:grid-cols-2">
        {tools.map((t) => (
          <Card
            key={t.name}
            data-testid={`tool-card-${t.name}`}
            className="border-slate-800 bg-slate-950/50"
          >
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm text-slate-200">
                <Wrench className="h-4 w-4 text-blue-400" />
                <code>{t.name}</code>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-slate-300">
                {TOOL_DESCRIPTIONS[t.name] ??
                  t.description ??
                  "No description."}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

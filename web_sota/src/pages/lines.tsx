import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";

interface Line {
  route_id: string;
  route_short_name?: string | null;
  route_long_name?: string | null;
  route_type?: number | string | null;
  route_color?: string | null;
  route_text_color?: string | null;
  agency_id?: string | null;
}

type TypeFilter = "all" | "1" | "0" | "3" | "2" | "other";

const FILTERS: { key: TypeFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "1", label: "U-Bahn" },
  { key: "0", label: "Tram" },
  { key: "3", label: "Bus" },
  { key: "2", label: "Rail" },
  { key: "other", label: "Other" },
];

const TYPE_LABELS: Record<string, string> = {
  "0": "Tram",
  "1": "U-Bahn",
  "2": "Rail",
  "3": "Bus",
  "4": "Ferry",
  "5": "Cable car",
  "6": "Gondola",
  "7": "Funicular",
  "11": "Trolleybus",
  "12": "Monorail",
};

function typeKey(t: number | string | null | undefined): string {
  const n = Number(t);
  return Number.isFinite(n) ? String(n) : "other";
}

function matchesFilter(line: Line, f: TypeFilter): boolean {
  if (f === "all") return true;
  const k = typeKey(line.route_type);
  if (f === "other") return !["0", "1", "2", "3"].includes(k);
  return k === f;
}

/** Agency hex color ("E30613") -> css color, with a neutral fallback. */
function dotColor(hex: string | null | undefined): string {
  if (hex && /^[0-9A-Fa-f]{6}$/.test(hex)) return `#${hex}`;
  return "#64748b"; // slate-500
}

export function Lines() {
  const [feeds, setFeeds] = useState<string[]>([]);
  const [feedId, setFeedId] = useState("");
  const [lines, setLines] = useState<Line[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<TypeFilter>("all");

  useEffect(() => {
    fetch(`${API_BASE}/v1/feeds`)
      .then((r) => r.json())
      .then((d: { id: string }[]) => {
        const ids = d.map((f) => f.id);
        setFeeds(ids);
        if (ids.length > 0) setFeedId(ids[0]);
        else setLoading(false);
      })
      .catch(() => {
        setFeeds([]);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!feedId) return;
    setLoading(true);
    setError(null);
    fetch(`${API_BASE}/v1/routes?feed_id=${encodeURIComponent(feedId)}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: { routes?: Line[] }) => {
        setLines(d.routes ?? []);
        setLoading(false);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Failed to load lines");
        setLines([]);
        setLoading(false);
      });
  }, [feedId]);

  const counts = useMemo(() => {
    const c: Record<TypeFilter, number> = {
      all: lines.length,
      "1": 0,
      "0": 0,
      "3": 0,
      "2": 0,
      other: 0,
    };
    for (const l of lines) {
      const k = typeKey(l.route_type);
      if (k === "1" || k === "0" || k === "3" || k === "2") c[k] += 1;
      else c.other += 1;
    }
    return c;
  }, [lines]);

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    return lines.filter((l) => {
      if (!matchesFilter(l, filter)) return false;
      if (q.length === 0) return true;
      return (
        (l.route_short_name || "").toLowerCase().includes(q) ||
        (l.route_long_name || "").toLowerCase().includes(q) ||
        (l.route_id || "").toLowerCase().includes(q)
      );
    });
  }, [lines, query, filter]);

  return (
    <div data-testid="lines-page" className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Lines</h2>
        <p className="text-sm text-slate-300">
          Every transit line in the feed - filter by vehicle type or search by
          name.
        </p>
      </div>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardContent>
          <div className="grid gap-3 pt-4 md:grid-cols-[180px_1fr]">
            <select
              data-testid="line-feed-select"
              value={feedId}
              onChange={(e) => setFeedId(e.target.value)}
              className="rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-zinc-100"
            >
              {feeds.length === 0 && <option value="">No feeds</option>}
              {feeds.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
            <label className="relative block">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
              />
              <input
                data-testid="line-search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search lines - e.g. U1, D, Badner Bahn"
                className="w-full rounded-lg border border-zinc-600 bg-zinc-800 py-2 pl-9 pr-3 text-sm text-zinc-100"
              />
            </label>
          </div>
          <div className="flex flex-wrap gap-2 pt-3">
            {FILTERS.map((f) => (
              <button
                key={f.key}
                type="button"
                data-testid={`line-filter-${f.key}`}
                onClick={() => setFilter(f.key)}
                className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                  filter === f.key
                    ? "border-blue-500 bg-blue-600/20 text-blue-200"
                    : "border-slate-700 text-slate-300 hover:bg-slate-800"
                }`}
              >
                {f.label} · {counts[f.key]}
              </button>
            ))}
          </div>
          {error && (
            <p className="mt-3 text-sm text-red-400" data-testid="lines-error">
              {error}
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader className="pb-2">
          <CardTitle
            className="text-sm text-slate-200"
            data-testid="lines-count"
          >
            {loading
              ? "Loading lines…"
              : `${visible.length} of ${lines.length} lines`}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading && <p className="text-sm text-slate-400">Loading…</p>}
          {!loading && visible.length === 0 && !error && (
            <p className="text-sm text-slate-400">
              No lines match - try a different search or filter.
            </p>
          )}
          <div className="max-h-[560px] space-y-1 overflow-y-auto">
            {visible.map((l) => (
              <div
                key={l.route_id}
                data-testid={`line-row-${l.route_id}`}
                className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2"
              >
                <span
                  className="h-3.5 w-3.5 shrink-0 rounded-full"
                  style={{ backgroundColor: dotColor(l.route_color ?? null) }}
                  title={
                    l.route_color ? `#${l.route_color}` : "no agency color"
                  }
                />
                <span className="w-16 shrink-0 text-sm font-bold text-slate-100">
                  {l.route_short_name || l.route_id}
                </span>
                <span className="min-w-0 flex-1 truncate text-sm text-slate-300">
                  {l.route_long_name || l.route_id}
                </span>
                <span className="shrink-0 rounded bg-slate-800 px-1.5 py-0.5 text-xs text-slate-400">
                  {TYPE_LABELS[typeKey(l.route_type)] ?? "Other"}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

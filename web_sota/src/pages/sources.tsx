import { BadgeCheck, Copy, Globe, KeyRound, Plus, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";

interface Preset {
  id: string;
  city: string;
  country: string;
  region: string;
  agency: string;
  url: string;
  timezone: string;
  language: string;
  license_url?: string;
  verified: boolean;
  needs_key: boolean;
  notes: string;
}

export function Sources() {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [region, setRegion] = useState("All");
  const [adding, setAdding] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/v1/presets`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: Preset[]) => {
        setPresets(d);
        setLoading(false);
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : "Failed to load presets");
        setLoading(false);
      });
  }, []);

  const regions = useMemo(
    () => ["All", ...Array.from(new Set(presets.map((p) => p.region)))],
    [presets],
  );

  const filtered = presets.filter((p) => {
    const q = query.trim().toLowerCase();
    const matchQ =
      q.length === 0 ||
      p.city.toLowerCase().includes(q) ||
      p.country.toLowerCase().includes(q) ||
      p.agency.toLowerCase().includes(q) ||
      p.id.toLowerCase().includes(q);
    const matchR = region === "All" || p.region === region;
    return matchQ && matchR;
  });

  const addPreset = async (p: Preset) => {
    setAdding(p.id);
    setMsg(null);
    try {
      const r = await fetch(`${API_BASE}/v1/feeds/from-preset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ preset_id: p.id }),
      });
      const data = (await r.json().catch(() => ({}))) as {
        detail?: string;
        message?: string;
      };
      if (!r.ok) {
        setMsg(`Could not add ${p.city}: ${data.detail ?? `HTTP ${r.status}`}`);
        return;
      }
      setMsg(
        `${p.city} added - parsing started. Watch progress on the Feeds depot page.`,
      );
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Request failed");
    } finally {
      setAdding(null);
    }
  };

  const copyUrl = (url: string) => {
    void navigator.clipboard?.writeText(url).catch(() => undefined);
  };

  return (
    <div data-testid="sources-page" className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">
          Sources
        </h2>
        <p className="text-sm text-slate-300">
          Curated GTFS starting points - Vienna is verified, the rest are
          best-effort community URLs. One click adds a feed; parsing progress
          shows on the{" "}
          <Link to="/feeds" className="text-blue-400 underline">
            Feeds depot
          </Link>{" "}
          page.
        </p>
      </div>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardContent>
          <div className="grid gap-3 pt-4 md:grid-cols-[1fr_200px]">
            <label className="relative block">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"
              />
              <input
                data-testid="preset-search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search city, country, agency - e.g. munich, paris, BART"
                className="w-full rounded-lg border border-zinc-600 bg-zinc-800 py-2 pl-9 pr-3 text-sm text-zinc-100"
              />
            </label>
            <select
              data-testid="preset-region"
              value={region}
              onChange={(e) => setRegion(e.target.value)}
              className="rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-2 text-sm text-zinc-100"
            >
              {regions.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          {msg && (
            <p
              data-testid="preset-message"
              className="mt-3 text-sm text-slate-300"
            >
              {msg}
            </p>
          )}
        </CardContent>
      </Card>

      {loading && (
        <p className="text-sm text-slate-400">Loading curated sources...</p>
      )}
      {error && (
        <p className="text-sm text-red-400" data-testid="sources-error">
          {error}
        </p>
      )}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {filtered.map((p) => (
          <Card
            key={p.id}
            data-testid={`preset-card-${p.id}`}
            className="border-slate-800 bg-slate-950/50"
          >
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center justify-between text-sm text-slate-200">
                <span className="flex items-center gap-2">
                  <Globe className="h-4 w-4 text-blue-400" />
                  {p.city}{" "}
                  <span className="font-normal text-slate-400">
                    ({p.country})
                  </span>
                </span>
                {p.verified ? (
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-xs text-emerald-400">
                    <BadgeCheck size={12} /> verified
                  </span>
                ) : (
                  <span className="rounded-full bg-slate-700/40 px-2 py-0.5 text-xs text-slate-300">
                    community
                  </span>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-sm text-slate-300">{p.agency}</p>
              <p className="truncate text-xs text-slate-400" title={p.url}>
                {p.url}
              </p>
              <p className="text-xs leading-relaxed text-slate-400">
                {p.notes}
              </p>
              <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-slate-300">
                <span className="rounded bg-slate-800 px-1.5 py-0.5">
                  {p.region}
                </span>
                <span className="rounded bg-slate-800 px-1.5 py-0.5">
                  {p.timezone}
                </span>
                {p.needs_key && (
                  <span className="inline-flex items-center gap-1 rounded bg-amber-500/10 px-1.5 py-0.5 text-amber-400">
                    <KeyRound size={11} /> API key needed
                  </span>
                )}
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  type="button"
                  data-testid={`preset-add-${p.id}`}
                  onClick={() => addPreset(p)}
                  disabled={adding === p.id}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-500 disabled:bg-zinc-700"
                >
                  <Plus size={13} />{" "}
                  {adding === p.id ? "Adding..." : "Add feed"}
                </button>
                <button
                  type="button"
                  data-testid={`preset-copy-${p.id}`}
                  onClick={() => copyUrl(p.url)}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
                >
                  <Copy size={13} /> Copy URL
                </button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {!loading && !error && filtered.length === 0 && (
        <p className="text-sm text-slate-400">
          No sources match - try a different search or region.
        </p>
      )}
    </div>
  );
}

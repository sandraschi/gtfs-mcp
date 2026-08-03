import { Bus, Clock, MapPin, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";

interface Stop {
  stop_id: string;
  stop_name: string;
  stop_code?: string | null;
  stop_lat?: number | null;
  stop_lon?: number | null;
  zone_id?: string | null;
  location_type?: number | null;
}

interface Departure {
  trip_id: string;
  route_id: string;
  route_short_name: string;
  route_long_name: string;
  trip_headsign: string;
  departure_time: string;
  stop_sequence: number;
  stop_id: string;
}

export function Stops() {
  const [feeds, setFeeds] = useState<string[]>([]);
  const [feedId, setFeedId] = useState("");
  const [query, setQuery] = useState("");
  const [stops, setStops] = useState<Stop[]>([]);
  const [selected, setSelected] = useState<Stop | null>(null);
  const [departures, setDepartures] = useState<Departure[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/v1/feeds`)
      .then((r) => r.json())
      .then((d: Feed[]) => {
        const ids = d.map((f) => f.id);
        setFeeds(ids);
        if (ids.length > 0) setFeedId(ids[0]);
      })
      .catch(() => setFeeds([]));
  }, []);

  interface Feed {
    id: string;
    url: string;
  }

  const search = useCallback(async () => {
    if (!feedId || !query.trim()) return;
    setLoading(true);
    setError(null);
    setSelected(null);
    setDepartures([]);
    try {
      const r = await fetch(
        `${API_BASE}/v1/stops/search?feed_id=${encodeURIComponent(feedId)}&query=${encodeURIComponent(query.trim())}&limit=20`,
      );
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setStops((await r.json()) as Stop[]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Search failed");
      setStops([]);
    } finally {
      setLoading(false);
    }
  }, [feedId, query]);

  const selectStop = async (stop: Stop) => {
    setSelected(stop);
    setDepartures([]);
    try {
      const r = await fetch(
        `${API_BASE}/v1/stops/${encodeURIComponent(stop.stop_id)}/departures?feed_id=${encodeURIComponent(feedId)}&limit=10`,
      );
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = (await r.json()) as { departures?: Departure[] };
      setDepartures(data.departures ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Departures failed");
    }
  };

  return (
    <div data-testid="stops-page" className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Stops</h2>
        <p className="text-sm text-slate-300">
          Search stops by name and inspect live schedule departures.
        </p>
      </div>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardContent>
          <div className="grid gap-3 md:grid-cols-[180px_1fr_auto]">
            <select
              data-testid="stop-feed-select"
              value={feedId}
              onChange={(e) => setFeedId(e.target.value)}
              className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded-lg px-3 py-2 text-sm"
            >
              {feeds.length === 0 && <option value="">No feeds</option>}
              {feeds.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
            <input
              data-testid="stop-search-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && search()}
              placeholder="Station name, e.g. Praterstern"
              className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded-lg px-3 py-2 text-sm"
            />
            <button
              type="button"
              data-testid="stop-search-button"
              onClick={search}
              disabled={loading || !feedId || !query.trim()}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 px-4 py-2 text-sm text-white"
            >
              <Search size={14} /> Search
            </button>
          </div>
          {error && (
            <p className="mt-3 text-sm text-red-400" data-testid="stops-error">
              {error}
            </p>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader>
            <CardTitle className="text-white">Results</CardTitle>
          </CardHeader>
          <CardContent>
            {loading && <p className="text-sm text-slate-400">Searching...</p>}
            {!loading && stops.length === 0 && !error && (
              <p className="text-sm text-slate-400">
                No stops yet - search to find stations.
              </p>
            )}
            <div className="max-h-[420px] space-y-1 overflow-y-auto">
              {stops.map((s) => (
                <button
                  type="button"
                  key={s.stop_id}
                  data-testid={`stop-result-${s.stop_id}`}
                  onClick={() => selectStop(s)}
                  className={`flex w-full items-start gap-2 rounded-lg border px-3 py-2 text-left text-sm transition-colors ${
                    selected?.stop_id === s.stop_id
                      ? "border-blue-600 bg-blue-600/10"
                      : "border-slate-800 bg-slate-900/40 hover:bg-slate-800"
                  }`}
                >
                  <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-blue-400" />
                  <span>
                    <span className="block text-slate-200">{s.stop_name}</span>
                    <span className="block text-xs text-slate-400">
                      {s.stop_id}
                      {s.stop_code ? ` | code ${s.stop_code}` : ""}
                      {s.stop_lat
                        ? ` | ${s.stop_lat.toFixed(4)}, ${s.stop_lon?.toFixed(4)}`
                        : ""}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-slate-800 bg-slate-950/50">
          <CardHeader>
            <CardTitle className="text-white">
              {selected ? selected.stop_name : "Departures"}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!selected && (
              <p className="text-sm text-slate-400">
                Select a stop to see its next departures.
              </p>
            )}
            {selected && departures.length === 0 && (
              <p className="text-sm text-slate-400">
                No departures in the next window for this stop.
              </p>
            )}
            <div className="space-y-1.5">
              {departures.map((d) => (
                <div
                  key={`${d.trip_id}-${d.departure_time}`}
                  data-testid="departure-row"
                  className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/40 px-3 py-2"
                >
                  <Bus className="h-4 w-4 shrink-0 text-emerald-500" />
                  <span className="w-10 text-sm font-semibold text-slate-200">
                    {d.route_short_name || d.route_id}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm text-slate-300">
                    {d.trip_headsign}
                  </span>
                  <span className="flex items-center gap-1 text-sm text-blue-400">
                    <Clock className="h-3.5 w-3.5" />
                    {new Date(d.departure_time).toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

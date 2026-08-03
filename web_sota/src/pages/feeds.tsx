import { Database, MapPin, Plus, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";

interface Feed {
  id: string;
  url: string;
  update_interval?: number;
  status?: string;
  last_updated?: string | null;
}

export function Feeds() {
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedId, setFeedId] = useState("");
  const [feedUrl, setFeedUrl] = useState("");
  const [interval, setIntervalV] = useState("3600");
  const [adding, setAdding] = useState(false);
  const [addMsg, setAddMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetch(`${API_BASE}/v1/feeds`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = (await r.json()) as Feed[];
      setFeeds(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load feeds");
      setFeeds([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const addFeed = async () => {
    if (!feedId.trim() || !feedUrl.trim()) return;
    setAdding(true);
    setAddMsg(null);
    try {
      const r = await fetch(`${API_BASE}/v1/feeds`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: feedId.trim(),
          url: feedUrl.trim(),
          update_interval: parseInt(interval, 10) || 3600,
        }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        setAddMsg(`Error: ${data.detail ?? data.error ?? `HTTP ${r.status}`}`);
        return;
      }
      setAddMsg(
        data.message ?? `Feed ${feedId.trim()} added - download started`,
      );
      setFeedId("");
      setFeedUrl("");
      load();
    } catch (e) {
      setAddMsg(e instanceof Error ? e.message : "Request failed");
    } finally {
      setAdding(false);
    }
  };

  return (
    <div data-testid="feeds-page" className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Feeds</h2>
        <p className="text-sm text-slate-300">
          Register GTFS feeds and monitor their download status.
        </p>
      </div>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader>
          <CardTitle className="text-white">Add Feed</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-[1fr_1.5fr_120px_auto]">
            <input
              data-testid="feed-id-input"
              value={feedId}
              onChange={(e) => setFeedId(e.target.value)}
              placeholder="Feed ID (e.g. wien)"
              className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded-lg px-3 py-2 text-sm"
            />
            <input
              data-testid="feed-url-input"
              value={feedUrl}
              onChange={(e) => setFeedUrl(e.target.value)}
              placeholder="https://agency.example/gtfs.zip"
              className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded-lg px-3 py-2 text-sm"
            />
            <input
              data-testid="feed-interval-input"
              value={interval}
              onChange={(e) => setIntervalV(e.target.value)}
              placeholder="3600"
              title="Update interval in seconds"
              className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded-lg px-3 py-2 text-sm"
            />
            <button
              type="button"
              data-testid="feed-add-button"
              onClick={addFeed}
              disabled={adding || !feedId.trim() || !feedUrl.trim()}
              className="inline-flex items-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-zinc-700 px-4 py-2 text-sm text-white"
            >
              <Plus size={14} /> {adding ? "Adding..." : "Add Feed"}
            </button>
          </div>
          {addMsg && (
            <p
              data-testid="feed-add-message"
              className="mt-3 text-sm text-slate-300"
            >
              {addMsg}
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-white">Registered Feeds</CardTitle>
          <button
            type="button"
            data-testid="feed-refresh-button"
            onClick={load}
            className="inline-flex items-center gap-1.5 rounded-md border border-slate-700 px-2.5 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
          >
            <RefreshCw size={12} /> Refresh
          </button>
        </CardHeader>
        <CardContent>
          {loading && <p className="text-sm text-slate-400">Loading...</p>}
          {error && (
            <p className="text-sm text-red-400" data-testid="feeds-error">
              {error}
            </p>
          )}
          {!loading && !error && feeds.length === 0 && (
            <div className="py-8 text-center">
              <Database className="mx-auto mb-3 h-10 w-10 text-slate-600" />
              <p className="text-sm text-slate-300">No feeds registered yet.</p>
              <p className="text-xs text-slate-400 mt-1">
                Add a feed above to start querying transit data.
              </p>
            </div>
          )}
          <div className="space-y-2">
            {feeds.map((f) => (
              <div
                key={f.id}
                data-testid={`feed-row-${f.id}`}
                className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-200">
                    <MapPin className="mr-1 inline h-3.5 w-3.5 text-blue-400" />
                    {f.id}
                  </p>
                  <p className="truncate text-xs text-slate-400">{f.url}</p>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-slate-400">
                    {f.update_interval
                      ? `every ${Math.round(f.update_interval / 60)} min`
                      : "n/a"}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 ${
                      f.status === "success"
                        ? "bg-emerald-500/10 text-emerald-400"
                        : f.status === "failed"
                          ? "bg-red-500/10 text-red-400"
                          : "bg-slate-700/40 text-slate-300"
                    }`}
                  >
                    {f.status ?? "pending"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

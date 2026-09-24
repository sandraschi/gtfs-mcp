import {
  Database,
  Download,
  MapPin,
  Plus,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE } from "@/lib/api";

interface Feed {
  id: string;
  url: string;
  update_interval?: number;
  status?: string;
  last_updated?: string | null;
  stops?: number;
  routes?: number;
  trips?: number;
  stop_times?: number;
  job_status?: string | null;
  job_stage?: string | null;
  job_progress?: number | null;
}

interface Job {
  feed_id: string;
  status: string;
  stage: string;
  progress: number;
  message: string;
  updated_at: string;
}

interface DepotStats {
  feed_count: number;
  total_stops: number;
  total_trips: number;
  total_stop_times: number;
}

function StageBar({
  progress,
  stage,
}: {
  progress: number | null | undefined;
  stage: string | null | undefined;
}) {
  if (progress == null || stage == null) return null;
  const pct = Math.round(progress * 100);
  const active = stage !== "done" && stage !== "failed";
  return (
    <div className="mt-2" data-testid="feed-progress">
      <div className="flex justify-between text-xs text-slate-300">
        <span className="capitalize">{stage.replace("_", " ")}</span>
        <span>{pct}%</span>
      </div>
      <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-800">
        <div
          className={`h-full rounded-full transition-all ${stage === "failed" ? "bg-red-500" : active ? "bg-blue-500" : "bg-emerald-500"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function Feeds() {
  const [feeds, setFeeds] = useState<Feed[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [stats, setStats] = useState<DepotStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedId, setFeedId] = useState("");
  const [feedUrl, setFeedUrl] = useState("");
  const [interval, setIntervalV] = useState("3600");
  const [adding, setAdding] = useState(false);
  const [addMsg, setAddMsg] = useState<string | null>(null);
  const [actionMsg, setActionMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [fr, jr, sr] = await Promise.all([
        fetch(`${API_BASE}/v1/feeds`),
        fetch(`${API_BASE}/v1/jobs`).catch(() => null),
        fetch(`${API_BASE}/v1/depot/stats`).catch(() => null),
      ]);
      if (!fr.ok) throw new Error(`HTTP ${fr.status}`);
      setFeeds((await fr.json()) as Feed[]);
      if (jr?.ok) setJobs((await jr.json()) as Job[]);
      if (sr?.ok) {
        const s = (await sr.json()) as DepotStats;
        setStats(s);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load feeds");
      setFeeds([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(() => {
      fetch(`${API_BASE}/v1/jobs`)
        .then((r) => (r.ok ? r.json() : []))
        .then((d: Job[]) => setJobs(d))
        .catch(() => undefined);
    }, 3000);
    return () => clearInterval(t);
  }, [load]);

  const jobFor = (id: string) => jobs.find((j) => j.feed_id === id);

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

  const doAction = async (kind: string, id: string) => {
    setBusy(`${kind}:${id}`);
    setActionMsg(null);
    try {
      let r: Response;
      if (kind === "delete") {
        r = await fetch(`${API_BASE}/v1/feeds/${encodeURIComponent(id)}`, {
          method: "DELETE",
        });
      } else if (kind === "refresh") {
        r = await fetch(
          `${API_BASE}/v1/feeds/${encodeURIComponent(id)}/refresh`,
          { method: "POST" },
        );
      } else {
        r = await fetch(
          `${API_BASE}/v1/feeds/${encodeURIComponent(id)}/export`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ target: "mywienerlinien" }),
          },
        );
      }
      const data = (await r.json().catch(() => ({}))) as {
        detail?: string;
        message?: string;
        dest?: string;
      };
      if (!r.ok) {
        setActionMsg(
          `${kind} ${id} failed: ${data.detail ?? `HTTP ${r.status}`}`,
        );
        return;
      }
      setActionMsg(
        data.message ??
          `${kind} ${id} ok${data.dest ? ` -> ${data.dest}` : ""}`,
      );
      load();
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div data-testid="feeds-page" className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white">
            Feeds depot
          </h2>
          <p className="text-sm text-slate-300">
            Parsed feeds live here (SQLite + data dir). Add manually, pick a{" "}
            <Link to="/sources" className="text-blue-400 underline">
              curated source
            </Link>
            , then refresh, delete, or export to mywienerlinien.
          </p>
        </div>
        {stats && (
          <div data-testid="depot-stats" className="flex gap-2">
            {[
              [`${stats.feed_count}`, "feeds"],
              [`${stats.total_stops.toLocaleString()}`, "stops"],
              [`${stats.total_trips.toLocaleString()}`, "trips"],
            ].map(([v, l]) => (
              <div
                key={l}
                className="rounded-xl border border-slate-700/60 bg-slate-900/60 px-3 py-1.5 text-center"
              >
                <p className="text-sm font-bold text-white">{v}</p>
                <p className="text-xs text-slate-400">{l}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {jobs.filter((j) => j.status === "running").length > 0 && (
        <Card className="border-blue-900/60 bg-blue-950/20">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-blue-300">
              Parsing now ({jobs.filter((j) => j.status === "running").length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {jobs
              .filter((j) => j.status === "running")
              .map((j) => (
                <div
                  key={j.feed_id}
                  data-testid={`job-row-${j.feed_id}`}
                  className="text-xs text-slate-300"
                >
                  <div className="flex justify-between">
                    <span className="font-medium text-slate-200">
                      {j.feed_id} -{" "}
                      <span className="capitalize">{j.stage}</span>
                    </span>
                    <span>{Math.round(j.progress * 100)}%</span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-800">
                    <div
                      className="h-full rounded-full bg-blue-500 transition-all"
                      style={{ width: `${Math.round(j.progress * 100)}%` }}
                    />
                  </div>
                  {j.message && (
                    <p className="mt-1 truncate text-slate-400">{j.message}</p>
                  )}
                </div>
              ))}
          </CardContent>
        </Card>
      )}

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
          {actionMsg && (
            <p
              data-testid="feed-action-message"
              className="mb-3 text-sm text-slate-300"
            >
              {actionMsg}
            </p>
          )}
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
                Add one above - or pick{" "}
                <Link to="/sources" className="text-blue-400 underline">
                  Vienna, Munich, London...
                </Link>{" "}
                from Sources.
              </p>
            </div>
          )}
          <div className="space-y-2">
            {feeds.map((f) => {
              const job = jobFor(f.id);
              const progress = job?.progress ?? f.job_progress;
              const stage = job?.stage ?? f.job_stage;
              return (
                <div
                  key={f.id}
                  data-testid={`feed-row-${f.id}`}
                  className="rounded-lg border border-slate-800 bg-slate-900/40 px-4 py-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-slate-200">
                        <MapPin className="mr-1 inline h-3.5 w-3.5 text-blue-400" />
                        {f.id}
                      </p>
                      <p className="truncate text-xs text-slate-400">{f.url}</p>
                      {(f.stops != null || f.trips != null) && (
                        <p className="mt-0.5 text-xs text-slate-400">
                          {(f.stops ?? 0).toLocaleString()} stops -{" "}
                          {(f.routes ?? 0).toLocaleString()} routes -{" "}
                          {(f.trips ?? 0).toLocaleString()} trips
                        </p>
                      )}
                      <StageBar progress={progress} stage={stage} />
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <button
                        type="button"
                        data-testid={`feed-refresh-${f.id}`}
                        title="Force re-download + re-parse"
                        onClick={() => doAction("refresh", f.id)}
                        disabled={busy === `refresh:${f.id}`}
                        className="rounded-md border border-slate-700 p-1.5 text-slate-300 hover:bg-slate-800 disabled:opacity-50"
                      >
                        <RefreshCw size={13} />
                      </button>
                      <button
                        type="button"
                        data-testid={`feed-export-${f.id}`}
                        title="Export to mywienerlinien (scripts/gtfs_data/cities/<id>)"
                        onClick={() => doAction("export", f.id)}
                        disabled={busy === `export:${f.id}`}
                        className="rounded-md border border-slate-700 p-1.5 text-slate-300 hover:bg-slate-800 disabled:opacity-50"
                      >
                        <Download size={13} />
                      </button>
                      <button
                        type="button"
                        data-testid={`feed-delete-${f.id}`}
                        title="Delete from depot"
                        onClick={() => doAction("delete", f.id)}
                        disabled={busy === `delete:${f.id}`}
                        className="rounded-md border border-red-900/60 p-1.5 text-red-400 hover:bg-red-950/40 disabled:opacity-50"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

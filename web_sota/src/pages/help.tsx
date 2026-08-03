import {
  Cpu,
  Globe,
  HelpCircle,
  Network,
  Server,
  Terminal,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const SECTIONS: Array<{
  icon: typeof Server;
  title: string;
  lines: string[];
}> = [
  {
    icon: Server,
    title: "Architecture",
    lines: [
      "FastMCP 3.4 server for GTFS transit schedule data.",
      "FastAPI backend: REST endpoints + MCP streamable HTTP at /mcp.",
      "7 MCP tools: add_feed, list_feeds, find_stops, get_departures, get_stop_info, status, shutdown.",
      "React webapp (Vite) talks to the backend over HTTP; MCP clients talk to /mcp.",
      "Optional Tauri desktop wrapper embeds the frozen backend.",
    ],
  },
  {
    icon: Network,
    title: "Ports",
    lines: [
      "Backend: 127.0.0.1:10913 (REST + /mcp + /health).",
      "Frontend: 127.0.0.1:10912 (Vite dev server, proxies /api, /mcp, /health).",
      "Registered in mcp-central-docs/operations/WEBAPP_PORTS.md.",
    ],
  },
  {
    icon: Cpu,
    title: "Environment",
    lines: [
      "Copy .env.example to .env at the repo root.",
      "GTFS_MCP_PORT / GTFS_MCP_HOST - backend binding (default 10913 / 127.0.0.1).",
      "GTFS_MCP_DEFAULT_FEED_URL - optional feed loaded at startup.",
      "GTFS_MCP_DISCOVERY__TRANSITFEEDS_API_KEY - feed discovery key.",
      "MCP_TRANSPORT=http with MCP_PORT=10913 - HTTP mode via python -m gtfs_mcp.",
    ],
  },
  {
    icon: Terminal,
    title: "Troubleshooting",
    lines: [
      "Webapp Offline: backend not running on 10913 - start with `uv run -m gtfs_mcp --http --port 10913`.",
      "add_feed fails: URL must serve a real GTFS zip; check with a browser.",
      "Empty departures: stop may have no stop_times or the feed lacks calendar data.",
      "Chat disabled: start Ollama (11434) or LM Studio (1234) and reload.",
      "Logs: /api/logs ring buffer or the Logging page.",
    ],
  },
  {
    icon: Globe,
    title: "Resources",
    lines: [
      "docs/CONFIGURATION.md - environment reference.",
      "docs/DEVELOPMENT.md - build, test, release.",
      "docs/TOOLS.md - full tool + endpoint tables.",
      "llms-full.txt - machine-readable server reference.",
      "mcp-central-docs/ - fleet standards and patterns.",
    ],
  },
];

export function Help() {
  return (
    <div data-testid="help-page" className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Help</h2>
        <p className="text-sm text-slate-300">
          How GTFS MCP works, where things live, and how to fix common issues.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {SECTIONS.map((s) => (
          <Card key={s.title} className="border-slate-800 bg-slate-950/50">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-sm text-slate-200">
                <s.icon className="h-4 w-4 text-blue-400" />
                {s.title}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1.5">
                {s.lines.map((line) => (
                  <li
                    key={line}
                    className="text-sm leading-relaxed text-slate-300"
                  >
                    {line}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="border-slate-800 bg-slate-950/50">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm text-slate-200">
            <HelpCircle className="h-4 w-4 text-blue-400" />
            Quick Start
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="list-decimal space-y-1.5 pl-5 text-sm text-slate-300">
            <li>
              Add a feed on the <strong>Feeds</strong> page (e.g. Wiener Linien
              GTFS zip).
            </li>
            <li>
              Search for a station on the <strong>Stops</strong> page and read
              its departures.
            </li>
            <li>
              Ask natural-language questions on the <strong>Chat</strong> page
              (requires a local LLM).
            </li>
            <li>
              Inspect the live tool surface on <strong>Tools</strong> and the
              skill docs on <strong>Skills</strong>.
            </li>
          </ol>
        </CardContent>
      </Card>
    </div>
  );
}

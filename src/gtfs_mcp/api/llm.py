"""Local LLM endpoints (Ollama / LM Studio) for the webapp Chat + Settings pages."""

import inspect
import json
import logging
from datetime import date
from typing import Any, cast

import aiohttp
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ..services import gtfs_service as _svc
from ..services.skills import get_skill_content

logger = logging.getLogger(__name__)

# Default chat model: small enough to leave VRAM headroom on a 24GB card,
# strong enough for reliable tool calls. Full Ollama name (as in /api/tags).
DEFAULT_MODEL = "pdurugyan/qwen3.5-9b-deepseek-v4-flash-Q4_K_M-v_2:latest"

# Agent context cap: our turns are short (capped tool outputs), so 16k is
# plenty. Without this, models load their default window (up to 262k) and
# Ollama reserves tens of GB of KV cache - the actual VRAM hog.
AGENT_NUM_CTX = 16384

router = APIRouter(prefix="/api/llm", tags=["llm"])

OLLAMA_BASE = "http://localhost:11434"
LMSTUDIO_BASE = "http://localhost:1234"

_PROVIDERS = [
    ("ollama", OLLAMA_BASE),
    ("lm_studio", LMSTUDIO_BASE),
]


async def _probe(base: str, path: str) -> bool:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base}{path}", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                return resp.status == 200
    except Exception:
        return False


async def _fetch_models(base: str) -> list[str]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base}/api/tags", timeout=aiohttp.ClientTimeout(total=3)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return [m.get("name", "") for m in data.get("models", []) if m.get("name")]
    except Exception:
        return []
    return []


@router.get("/providers")
@router.get("/discover")
async def discover_providers():
    """Probe Ollama + LM Studio; return per-provider model lists."""
    results: dict = {}
    for name, base in _PROVIDERS:
        if await _probe(base, "/v1/models" if name == "lm_studio" else "/api/tags"):
            models = await _fetch_models(base)
            if not models and name == "ollama":
                models = ["llama3.2:3b"]
            results[name] = models
        else:
            results[name] = []
    results["detected"] = [name for name, _ in _PROVIDERS if results[name]]
    return results


class ChatRequest(BaseModel):
    model: str = DEFAULT_MODEL
    messages: list[dict]
    system: str | None = None


async def _stream_ollama(req: ChatRequest):
    """Stream NDJSON chunks from Ollama /api/chat."""
    payload = {
        "model": req.model,
        "messages": req.messages,
        "stream": True,
    }
    if req.system:
        payload["system"] = req.system
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_BASE}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    yield json.dumps({"error": f"Ollama HTTP {resp.status}: {body[:200]}"}) + "\n"
                    return
                async for line in resp.content:
                    if line.strip():
                        yield line.decode("utf-8", errors="replace")
    except Exception as e:
        yield json.dumps({"error": f"Ollama unreachable: {e}"}) + "\n"


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """Proxy chat completions to Ollama, streaming NDJSON back to the browser."""
    return StreamingResponse(
        _stream_ollama(req),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache"},
    )


async def _chat_once(req: ChatRequest) -> dict:
    payload = {
        "model": req.model,
        "messages": req.messages,
        "stream": False,
    }
    if req.system:
        payload["system"] = req.system
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{OLLAMA_BASE}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"success": True, "content": data.get("message", {}).get("content", "")}
                return {
                    "success": False,
                    "message": f"Ollama HTTP {resp.status}",
                    "error": f"Ollama HTTP {resp.status}",
                }
    except Exception as e:
        return {"success": False, "message": f"Ollama unreachable: {e}", "error": f"Ollama unreachable: {e}"}


@router.post("/chat")
async def chat_once(req: ChatRequest):
    """Non-streaming chat completion (fallback for simple clients)."""
    return await _chat_once(req)


# ---------------------------------------------------------------------------
# Agentic chat: Ollama native tool loop against the live GTFS depot.
#
# The plain /chat/stream proxy sends the model zero context and no tools, so
# small models free-associate ("Praterstern? never heard of it - Berlin?").
# This endpoint injects the skill + depot state into the system prompt and
# lets the model call find_stops / get_departures / get_stop_info /
# list_feeds, executing them in-process. Max 6 model turns per request.
# ---------------------------------------------------------------------------

_AGENT_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_feeds",
            "description": "List registered GTFS feeds (ids, cities, stop/route counts). Call first when unsure which feed to use.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_stops",
            "description": "Search stops by name/code/id (case-insensitive). Always resolve a prose stop name with this before asking departures.",
            "parameters": {
                "type": "object",
                "properties": {
                    "feed_id": {"type": "string", "description": "Feed id, e.g. default"},
                    "query": {"type": "string", "description": "Stop name fragment, e.g. Praterstern"},
                    "limit": {"type": "integer", "description": "Max results (1-100)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_departures",
            "description": "Upcoming departures for a stop_id from find_stops. Never invent times.",
            "parameters": {
                "type": "object",
                "properties": {
                    "feed_id": {"type": "string"},
                    "stop_id": {"type": "string"},
                    "route_id": {"type": "string"},
                    "limit": {"type": "integer"},
                },
                "required": ["stop_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stop_info",
            "description": "Details for one stop_id (coordinates, zone).",
            "parameters": {
                "type": "object",
                "properties": {
                    "feed_id": {"type": "string"},
                    "stop_id": {"type": "string"},
                },
                "required": ["stop_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Public web search for anything OUTSIDE the schedule depot: news, reviews, comparisons, background. Use for questions the depot cannot answer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Max results (1-10)"},
                },
                "required": ["query"],
            },
        },
    },
]

_AGENT_FUNCS = {
    "list_feeds": "list_feeds",
    "find_stops": "find_stops",
    "get_departures": "get_departures",
    "get_stop_info": "get_stop_info",
    "web_search": "web_search",
}

_AGENT_MAX_TURNS = 6


async def _default_feed_id() -> str:
    """First registered feed id, falling back to 'default'."""
    try:
        fm = _svc.feed_manager
        if fm is not None:
            feeds = fm.list_feeds()
            if feeds:
                return str(feeds[0].get("id") or "default")
    except Exception:
        logger.exception("Failed to determine default feed id")
    return "default"


def _agent_system(personality: str, custom_prompt: str = "") -> str:
    """System prompt: role + skill content + live depot state + today's date."""
    feeds_desc = "none loaded"
    try:
        fm = _svc.feed_manager
        if fm is not None:
            parts = [f"{f['id']} ({f.get('stops', 0)} stops)" for f in fm.list_feeds()]
            feeds_desc = "; ".join(parts) or "none loaded"
    except Exception:
        logger.exception("Failed to build loaded-feeds description")
    skill = get_skill_content("gtfs-transit-expert")
    base = (
        "You are the transit assistant for GTFS MCP, a live schedule server. "
        f"Today is {date.today().isoformat()}. Our home city is Vienna, Austria - "
        "assume Vienna unless the user names another city. "
        f"Loaded feeds: {feeds_desc}. "
        "MANDATORY PROCEDURE, no exceptions: (1) for any named stop call "
        "find_stops first; (2) for departures call get_departures with the "
        "returned stop_id; (3) answer ONLY from tool results. Never state a "
        "time, line, or stop you did not receive from a tool - a rounded "
        "guess like ':10 / :30' is always wrong. If tools return nothing, "
        "say what you checked and stop. "
        "Keep answers short and name the stop and line for every departure. "
        "Call data tools only when the user's question needs them - never "
        "fetch transit data unprompted and never paste tool examples from "
        "the skill as real queries. Answer only what was asked. "
        "For questions the depot cannot answer (news, reviews, comparisons, "
        "general knowledge) use web_search and name your sources. "
        "Your visible reply is always plain sentences for a transit rider - "
        "never JSON, code blocks, or tool-call syntax."
    )
    if personality and personality != "Custom":
        base += f" Style: {personality}."
    if custom_prompt.strip():
        base += f" Extra user instructions: {custom_prompt.strip()}"
    return f"{base}\n\n--- skill: gtfs-transit-expert ---\n{skill}"


def _trace_summary(name: str, result: dict) -> str:
    """One-line human summary of a tool result for the chat trace display."""
    if not result.get("success", False):
        return f"failed: {result.get('error', 'unknown error')}"[:160]
    if name == "find_stops":
        stops = result.get("stops", [])
        first = stops[0].get("stop_name", "") if stops else ""
        return f"{len(stops)} stop(s)" + (f" - first: {first}" if first else "")
    if name == "get_departures":
        deps = result.get("departures", [])
        first = ""
        if deps:
            first = f"{deps[0].get('route_short_name', '')} to {deps[0].get('trip_headsign', '')}"
        return f"{len(deps)} departure(s)" + (f" - next {first}" if first else "")
    if name == "list_feeds":
        return f"{len(result.get('feeds', []))} feed(s)"
    if name == "get_stop_info":
        stop = result.get("stop") or {}
        return str(stop.get("stop_name") or "ok")
    if name == "web_search":
        results = result.get("results", [])
        first = results[0].get("title", "") if results else ""
        return f"{len(results)} web result(s)" + (f" - top: {first[:80]}" if first else "")
    return "ok"


async def _exec_agent_tool(name: str, args: dict) -> dict:
    """Execute one agent tool call against the live service functions."""
    attr = _AGENT_FUNCS.get(name)
    fn: Any = getattr(_svc, attr, None) if attr else None
    if fn is None or not callable(fn):
        return {"success": False, "message": f"unknown tool: {name}", "error": f"unknown tool: {name}"}
    params = dict(args or {})
    if not params.get("feed_id"):
        params["feed_id"] = await _default_feed_id()
    try:
        known = set(inspect.signature(fn).parameters)
    except (TypeError, ValueError):
        known = set()
    params = {k: v for k, v in params.items() if k in known}
    if "limit" in params:
        try:
            params["limit"] = max(1, min(100, int(params["limit"])))
        except (TypeError, ValueError):
            params["limit"] = 10
    try:
        result = await cast(Any, fn)(**params)
        return result if isinstance(result, dict) else {"success": True, "result": result}
    except Exception as e:
        logger.exception("agent tool %s failed", name)
        return {"success": False, "message": f"{name} failed: {e!s}", "error": f"{name} failed: {e!s}"}


async def _ollama_agent_turn(
    session: aiohttp.ClientSession, model: str, system: str, messages: list[dict], with_tools: bool = True
) -> dict:
    """One non-streaming Ollama chat call, optionally with tools attached."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "system": system,
        "options": {"num_ctx": AGENT_NUM_CTX},
    }
    if with_tools:
        payload["tools"] = _AGENT_TOOLS
    async with session.post(
        f"{OLLAMA_BASE}/api/chat",
        json=payload,
        timeout=aiohttp.ClientTimeout(total=180),
    ) as resp:
        if resp.status != 200:
            raise RuntimeError(f"Ollama HTTP {resp.status}: {(await resp.text())[:200]}")
        data = await resp.json()
        message = data.get("message", {})
        return message if isinstance(message, dict) else {}


def _looks_like_tool_leak(text: str) -> bool:
    """Detect raw pseudo-tool syntax leaking into the visible reply."""
    t = text or ""
    return (
        "[TOOL_CALLS]" in t
        or ("```" in t and "tool" in t.lower())
        or ('"departures"' in t and t.strip().startswith("{"))
    )


async def _ensure_plain_text(
    session: aiohttp.ClientSession, model: str, system: str, messages: list[dict], content: str
) -> str:
    """One no-tools restate turn when the model leaks tool syntax. Falls back
    to the original content rather than failing the whole request."""
    if not _looks_like_tool_leak(content):
        return content
    try:
        retry = [
            *messages,
            {
                "role": "user",
                "content": "Restate that as plain sentences for a transit rider. "
                "No JSON, no code blocks, no tool syntax, no bracket tags.",
            },
        ]
        msg = await _ollama_agent_turn(session, model, system, retry, with_tools=False)
        text = (msg.get("content") or "").strip()
        return text if text and not _looks_like_tool_leak(text) else content
    except Exception:
        return content


class AgentRequest(BaseModel):
    model: str = DEFAULT_MODEL
    messages: list[dict] = []
    personality: str = "Transit Analyst"
    custom_prompt: str = ""


async def _prefetch_stop_data(user_text: str) -> dict | None:
    """Deterministic shortcut: if the user names a loaded stop, fetch its
    departures directly and hand the model real data to verbalize.

    Weak tool-models often fumble the find_stops->get_departures chain (or
    emit pseudo-calls like [TOOL_CALLS]{...} with invented times). Matching
    against the depot up front guarantees grounded answers regardless.
    Returns None when no stop name matches.
    """
    try:
        fm = _svc.feed_manager
        if fm is None:
            return None
        feeds = fm.list_feeds()
        if not feeds:
            return None
        feed_id = str(feeds[0].get("id") or "default")
        feed = fm.get_feed(feed_id)
        if feed is None or not feed.stops:
            return None
        text = user_text.lower()
        best: str | None = None
        for stop in feed.stops:
            name = str(stop.get("stop_name") or "")
            if len(name) >= 4 and name.lower() in text:
                if best is None or len(name) > len(best):
                    best = name
        if best is None:
            return None
        found = await _svc.find_stops(feed_id=feed_id, query=best, limit=5)
        stops = found.get("stops", []) if isinstance(found, dict) else []
        if not stops:
            return None
        first = stops[0]
        deps = await _svc.get_departures(feed_id=feed_id, stop_id=str(first.get("stop_id", "")), limit=5)
        departures = deps.get("departures", []) if isinstance(deps, dict) else []
        return {"feed_id": feed_id, "stop": first, "stops": stops, "departures": departures}
    except Exception:
        logger.exception("stop prefetch failed")
        return None


@router.post("/chat-agent")
async def chat_agent(req: AgentRequest):
    """Agentic chat: model + tools loop, returns final reply with a tool trace."""
    system = _agent_system(req.personality, req.custom_prompt)
    messages = [
        {"role": m.get("role", "user"), "content": str(m.get("content", ""))}
        for m in req.messages[-20:]
        if m.get("role") in ("user", "assistant")
    ]
    trace: list[dict] = []
    data_calls = 0
    nudges = 0
    # Deterministic grounding first: real departures in context even if the
    # model never manages a correct tool call.
    last_user = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
    prefetched = await _prefetch_stop_data(str(last_user))
    if prefetched:
        stop_name = str(prefetched["stop"].get("stop_name") or "?")
        deps = prefetched["departures"]
        if deps:
            data_msg = (
                "[Live depot data - summarize exactly this, invent nothing. "
                "Answer in plain sentences, no JSON, no tool syntax. "
                f"{json.dumps(prefetched, default=str)[:6000]}]"
            )
        else:
            data_msg = (
                f"[Live depot data: stop {stop_name} was found, but it has "
                "ZERO upcoming departures scheduled right now (likely night "
                "break). Tell the user plainly that nothing is coming at the "
                "moment. NEVER estimate, round, or invent a time like 'in 7 "
                "minutes' - that would be a lie. Answer in plain sentences, "
                "no JSON, no tool syntax.]"
            )
        messages.append({"role": "user", "content": data_msg})
        trace.append(
            {
                "tool": "depot-prefetch",
                "ok": True,
                "summary": f"{stop_name} ({prefetched['stop'].get('stop_id')}) - {len(deps)} departure(s)",
            }
        )
        data_calls += 1
    try:
        async with aiohttp.ClientSession() as session:
            for _ in range(_AGENT_MAX_TURNS):
                message = await _ollama_agent_turn(session, req.model, system, messages)
                calls = message.get("tool_calls") or []
                content = message.get("content") or ""
                messages.append({"role": "assistant", "content": content})
                if not calls:
                    # Model tried to answer from thin air: send it back to fetch data.
                    if data_calls == 0 and nudges < 2:
                        nudges += 1
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "(System reminder, not the user: you have not called "
                                    "any data tool yet. Call find_stops and get_departures "
                                    "now - do not answer without tool results.)"
                                ),
                            }
                        )
                        continue
                    reply = await _ensure_plain_text(session, req.model, system, messages, content)
                    return {"success": True, "reply": reply, "trace": trace}
                for call in calls:
                    func = call.get("function", {}) if isinstance(call, dict) else {}
                    name = str(func.get("name", ""))
                    raw_args = func.get("arguments", {})
                    if isinstance(raw_args, str):
                        try:
                            raw_args = json.loads(raw_args)
                        except json.JSONDecodeError:
                            raw_args = {}
                    result = await _exec_agent_tool(name, raw_args if isinstance(raw_args, dict) else {})
                    ok = bool(result.get("success", False))
                    if ok and name in ("find_stops", "get_departures", "get_stop_info"):
                        data_calls += 1
                    trace.append(
                        {
                            "tool": name,
                            "ok": bool(result.get("success", False)),
                            "summary": _trace_summary(name, result),
                        }
                    )
                    messages.append({"role": "tool", "content": json.dumps(result, default=str)[:8000]})
            return {
                "success": True,
                "reply": "I ran out of steps before finishing - try a more specific question.",
                "trace": trace,
            }
    except Exception as e:
        logger.exception("chat-agent failed")
        return {"success": False, "message": str(e), "error": str(e), "trace": trace}

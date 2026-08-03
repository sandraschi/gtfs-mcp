"""Local LLM endpoints (Ollama / LM Studio) for the webapp Chat + Settings pages."""

import json
import logging

import aiohttp
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

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
    model: str = "llama3.2:3b"
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
                return {"success": False, "error": f"Ollama HTTP {resp.status}"}
    except Exception as e:
        return {"success": False, "error": f"Ollama unreachable: {e}"}


@router.post("/chat")
async def chat_once(req: ChatRequest):
    """Non-streaming chat completion (fallback for simple clients)."""
    return await _chat_once(req)

"""JARVIS FastAPI Backend Server.

Provides:
- REST API for frontend communication
- WebSocket endpoint for real-time events (state, transcripts, system metrics)
- Bridges the existing JARVIS core (assistant, brain, voice, security) with the React frontend
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import psutil
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import PermissionType, settings
from core.assistant import JarvisAssistant
from core.command_router import CommandRouter

logger = logging.getLogger("jarvis.api.server")

# ---------------------------------------------------------------------------
# Global application state
# ---------------------------------------------------------------------------

_assistant: Optional[JarvisAssistant] = None
_router: Optional[CommandRouter] = None
_ws_clients: List[WebSocket] = []
_startup_time: float = time.time()


# ---------------------------------------------------------------------------
# WebSocket broadcast helper
# ---------------------------------------------------------------------------

async def broadcast(event: str, data: Dict[str, Any]) -> None:
    """Broadcast a JSON event to all connected WebSocket clients."""
    message = json.dumps({"event": event, "data": data, "ts": time.time()})
    dead: List[WebSocket] = []
    for ws in _ws_clients:
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _ws_clients.remove(ws)


def get_assistant() -> JarvisAssistant:
    if _assistant is None:
        raise RuntimeError("Assistant not initialized")
    return _assistant


# ---------------------------------------------------------------------------
# Lifespan: start/stop JARVIS core on server startup/shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _assistant, _router

    logger.info("Initializing JARVIS core from FastAPI lifespan...")
    _assistant = JarvisAssistant()
    _router = CommandRouter(_assistant)

    # Hook voice state changes → broadcast to WebSocket clients
    def on_voice_state(old, new):
        asyncio.ensure_future(broadcast("voice_state", {
            "old": old.value,
            "new": new.value,
            "is_muted": _assistant.voice.is_muted if _assistant else False,
            "seconds_until_sleep": _assistant.voice.seconds_until_sleep if _assistant else 0.0,
        }))

    _assistant.voice.add_state_listener(on_voice_state)

    # Hook AI provider fallback → broadcast to WebSocket clients
    if hasattr(_assistant.brain.provider, "add_fallback_listener"):
        def on_provider_fallback(data: Dict[str, Any]):
            asyncio.ensure_future(broadcast("provider_fallback", data))

        _assistant.brain.provider.add_fallback_listener(on_provider_fallback)

    logger.info("JARVIS API server ready.")
    yield

    logger.info("Shutting down JARVIS core...")
    if _assistant:
        _assistant.shutdown()


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="JARVIS API",
    description="Backend API for the JARVIS personal AI assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Dev only — frontend on localhost:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CommandRequest(BaseModel):
    command: str

class CommandResponse(BaseModel):
    response: str
    success: bool

class PermissionUpdateRequest(BaseModel):
    permission: str
    state: str  # "allow" | "block"
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Health / Status
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - _startup_time, 1),
        "version": settings.version,
    }


@app.get("/api/status")
async def get_status() -> Dict[str, Any]:
    """Full JARVIS diagnostic report for the dashboard."""
    assistant = get_assistant()
    report = assistant.get_status_report()

    # Augment with live system metrics
    vm = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=None)
    report["system_cpu_percent"] = cpu
    report["system_ram_used_gb"] = round((vm.total - vm.available) / (1024 ** 3), 2)
    report["system_ram_total_gb"] = round(vm.total / (1024 ** 3), 2)
    report["system_ram_percent"] = vm.percent

    return report


# ---------------------------------------------------------------------------
# Command execution
# ---------------------------------------------------------------------------

@app.post("/api/command")
async def execute_command(req: CommandRequest) -> CommandResponse:
    """Execute a text command through the full JARVIS pipeline."""
    if not req.command.strip():
        raise HTTPException(status_code=400, detail="Empty command")
    assistant = get_assistant()
    assistant.voice.reset_activity()
    try:
        response = await _router.handle_command(req.command.strip())  # type: ignore[union-attr]

        # Broadcast transcript event
        await broadcast("transcript", {
            "role": "user",
            "text": req.command.strip(),
        })
        await broadcast("transcript", {
            "role": "assistant",
            "text": response or "",
        })
        return CommandResponse(response=response or "Done.", success=True)
    except Exception as exc:
        logger.error(f"Command error: {exc}")
        return CommandResponse(response=f"Error: {exc}", success=False)


# ---------------------------------------------------------------------------
# Voice controls
# ---------------------------------------------------------------------------

@app.post("/api/voice/start")
async def start_voice() -> Dict[str, Any]:
    assistant = get_assistant()
    success = assistant.voice.start_listening()
    return {"success": success, "state": assistant.voice.state.value}


@app.post("/api/voice/stop")
async def stop_voice() -> Dict[str, Any]:
    assistant = get_assistant()
    assistant.voice.stop_listening()
    return {"success": True, "state": assistant.voice.state.value}


@app.post("/api/voice/interrupt")
async def interrupt_voice() -> Dict[str, Any]:
    assistant = get_assistant()
    interrupted = assistant.voice.interrupt()
    return {"interrupted": interrupted, "state": assistant.voice.state.value}


@app.get("/api/voice/state")
async def get_voice_state() -> Dict[str, Any]:
    assistant = get_assistant()
    return {
        "state": assistant.voice.state.value,
        "is_muted": assistant.voice.is_muted,
        "seconds_until_sleep": assistant.voice.seconds_until_sleep,
        "inactivity_timeout_seconds": assistant.voice.inactivity_timeout_seconds,
    }


@app.post("/api/voice/mute")
async def mute_voice() -> Dict[str, Any]:
    assistant = get_assistant()
    assistant.voice.mute()
    await broadcast("voice_state", {
        "old": "AWAKE",
        "new": assistant.voice.state.value,
        "is_muted": True,
        "seconds_until_sleep": 0.0,
    })
    return {"muted": True, "state": assistant.voice.state.value}


@app.post("/api/voice/unmute")
async def unmute_voice() -> Dict[str, Any]:
    assistant = get_assistant()
    success = assistant.voice.unmute()
    await broadcast("voice_state", {
        "old": "MIC_DISABLED",
        "new": assistant.voice.state.value,
        "is_muted": False,
        "seconds_until_sleep": assistant.voice.seconds_until_sleep,
    })
    return {"muted": False, "success": success, "state": assistant.voice.state.value}


@app.post("/api/voice/toggle-mute")
async def toggle_mute_voice() -> Dict[str, Any]:
    assistant = get_assistant()
    is_muted = assistant.voice.toggle_mute()
    await broadcast("voice_state", {
        "old": "MIC_DISABLED" if not is_muted else "AWAKE",
        "new": assistant.voice.state.value,
        "is_muted": is_muted,
        "seconds_until_sleep": assistant.voice.seconds_until_sleep,
    })
    return {"muted": is_muted, "state": assistant.voice.state.value}


@app.post("/api/voice/wake")
async def wake_voice() -> Dict[str, Any]:
    assistant = get_assistant()
    success = assistant.voice.wake_up()
    await broadcast("voice_state", {
        "old": "SLEEP",
        "new": assistant.voice.state.value,
        "is_muted": assistant.voice.is_muted,
        "seconds_until_sleep": assistant.voice.seconds_until_sleep,
    })
    return {"success": success, "state": assistant.voice.state.value}


@app.post("/api/voice/sleep")
async def sleep_voice() -> Dict[str, Any]:
    assistant = get_assistant()
    assistant.voice.sleep()
    await broadcast("voice_state", {
        "old": "AWAKE",
        "new": assistant.voice.state.value,
        "is_muted": assistant.voice.is_muted,
        "seconds_until_sleep": 0.0,
    })
    return {"success": True, "state": assistant.voice.state.value}


# ---------------------------------------------------------------------------
# Security controls
# ---------------------------------------------------------------------------

@app.post("/api/security/emergency-stop")
async def emergency_stop() -> Dict[str, Any]:
    assistant = get_assistant()
    assistant.security.trigger_emergency_stop("User triggered emergency stop from UI")
    assistant.voice.stop_listening()
    await broadcast("emergency_stop", {"active": True})
    return {"success": True, "emergency_stopped": True}


@app.post("/api/security/reset-emergency-stop")
async def reset_emergency_stop() -> Dict[str, Any]:
    assistant = get_assistant()
    assistant.security.reset_emergency_stop()
    await broadcast("emergency_stop", {"active": False})
    return {"success": True, "emergency_stopped": False}


@app.post("/api/security/safe-mode/enable")
async def enable_safe_mode() -> Dict[str, Any]:
    assistant = get_assistant()
    assistant.security.set_safe_mode(True)
    return {"success": True, "safe_mode": True}


@app.post("/api/security/safe-mode/disable")
async def disable_safe_mode() -> Dict[str, Any]:
    assistant = get_assistant()
    assistant.security.set_safe_mode(False)
    return {"success": True, "safe_mode": False}


# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

@app.get("/api/permissions")
async def get_permissions() -> Dict[str, Any]:
    assistant = get_assistant()
    return {"permissions": assistant.permissions.get_all_statuses()}


@app.post("/api/permissions/update")
async def update_permission(req: PermissionUpdateRequest) -> Dict[str, Any]:
    assistant = get_assistant()
    assistant.voice.reset_activity()
    try:
        perm_type = PermissionType(req.permission)
        if req.state == "allow":
            assistant.permissions.allow(perm_type, req.reason or "Granted from UI")
        elif req.state == "block":
            assistant.permissions.block(perm_type, req.reason or "Blocked from UI")
        else:
            raise HTTPException(status_code=400, detail=f"Unknown state: {req.state}")

        await broadcast("permission_update", {
            "permission": req.permission,
            "state": req.state,
        })
        return {"success": True, "permission": req.permission, "state": req.state}
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown permission: {req.permission}")


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

@app.get("/api/memory")
async def get_memories() -> Dict[str, Any]:
    assistant = get_assistant()
    assistant.voice.reset_activity()
    try:
        memories = assistant.memory.list_memories()
        return {"memories": [m.__dict__ if hasattr(m, "__dict__") else m for m in memories]}
    except Exception as exc:
        return {"memories": [], "error": str(exc)}


@app.delete("/api/memory/{memory_id}")
async def delete_memory(memory_id: str) -> Dict[str, Any]:
    assistant = get_assistant()
    assistant.voice.reset_activity()
    try:
        result = assistant.memory.delete_memory(memory_id)
        return {"success": bool(result)}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/conversations")
async def get_conversations() -> Dict[str, Any]:
    assistant = get_assistant()
    assistant.voice.reset_activity()
    try:
        session_id = assistant.context.get_current_session_id()
        messages = assistant.conversations.get_recent_messages(session_id=session_id, limit=50)
        return {"messages": [m.__dict__ if hasattr(m, "__dict__") else m for m in messages]}
    except Exception as exc:
        return {"messages": [], "error": str(exc)}


# ---------------------------------------------------------------------------
# Audit logs
# ---------------------------------------------------------------------------

@app.get("/api/logs")
async def get_audit_logs(limit: int = 50) -> Dict[str, Any]:
    assistant = get_assistant()
    assistant.voice.reset_activity()
    try:
        logs = [e.model_dump() for e in assistant.audit.get_recent_entries(limit=limit)]
        return {"logs": logs}
    except Exception as exc:
        return {"logs": [], "error": str(exc)}


# ---------------------------------------------------------------------------
# WebSocket: real-time event stream
# ---------------------------------------------------------------------------

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await websocket.accept()
    _ws_clients.append(websocket)
    logger.info(f"WebSocket client connected. Total: {len(_ws_clients)}")

    # Send initial state
    try:
        assistant = get_assistant()
        report = assistant.get_status_report()
        await websocket.send_text(json.dumps({
            "event": "connected",
            "data": {
                "voice_state": report["voice_state"],
                "safe_mode": report["safe_mode"],
                "emergency_stopped": report["emergency_stopped"],
                "ai_provider": report.get("ai_provider"),
                "ai_active_provider": report.get("ai_active_provider"),
                "ai_fallback_active": report.get("ai_fallback_active", False),
                "ai_fallback_reason": report.get("ai_fallback_reason"),
            },
            "ts": time.time(),
        }))
    except Exception:
        pass

    try:
        while True:
            # Keep alive + handle incoming messages
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                data = json.loads(msg)
                # Handle ping
                if data.get("type") == "ping":
                    await websocket.send_text(json.dumps({"event": "pong", "ts": time.time()}))
            except asyncio.TimeoutError:
                # Send heartbeat
                await websocket.send_text(json.dumps({"event": "heartbeat", "ts": time.time()}))
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning(f"WebSocket error: {exc}")
    finally:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)
        logger.info(f"WebSocket client disconnected. Total: {len(_ws_clients)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_server(host: str = "127.0.0.1", port: int = 8765, reload: bool = False) -> None:
    """Start the JARVIS API server."""
    uvicorn.run(
        "api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    run_server(port=port)

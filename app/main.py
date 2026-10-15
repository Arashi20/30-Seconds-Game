"""FastAPI server: HTTP to create/join rooms, a WebSocket per player for live state.

All state lives in memory, so run a single worker (the default for uvicorn).
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.game import DEFAULT_TARGET, TURN_SECONDS, GameError, Room, new_room_code

STATIC_DIR = Path(__file__).parent.parent / "static"
ROOM_TTL_SECONDS = 6 * 3600
# A dropped connection is only announced after a short grace period, so a phone
# that locks its screen for a moment doesn't spam everyone. If the host stays
# away a bit longer, the host role moves to someone who is still connected.
OFFLINE_NOTICE_SECONDS = 5
HOST_HANDOVER_SECONDS = 15

app = FastAPI(title="30 Seconds")


@app.middleware("http")
async def always_revalidate(request, call_next):
    """Make browsers check for a newer version of the page, CSS and JS on every
    load. Unchanged files still come from the cache (a quick 304 response), but
    after an update every phone gets the new version straight away."""
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response
rooms: dict[str, Room] = {}
# room code -> {player_id: websocket}
sockets: dict[str, dict[str, WebSocket]] = {}
# (room code, player_id) of players whose disconnect was announced
announced_offline: set[tuple[str, str]] = set()


class CreateRoom(BaseModel):
    name: str
    lang: str = "nl"
    teams: int = 2
    target: int = DEFAULT_TARGET


class JoinRoom(BaseModel):
    name: str


def cleanup_rooms() -> None:
    cutoff = time.time() - ROOM_TTL_SECONDS
    for code in [c for c, r in rooms.items() if r.last_activity < cutoff and not sockets.get(c)]:
        rooms.pop(code, None)
        sockets.pop(code, None)


def get_room(code: str) -> Room:
    room = rooms.get(code.upper())
    if room is None:
        raise HTTPException(404, "Room not found")
    return room


@app.post("/api/rooms")
def create_room(body: CreateRoom):
    cleanup_rooms()
    try:
        room = Room(new_room_code(rooms), lang=body.lang, num_teams=body.teams, target=body.target)
        player = room.add_player(body.name)
    except GameError as e:
        raise HTTPException(400, str(e)) from None
    rooms[room.code] = room
    return {"code": room.code, "player_id": player.id}


@app.post("/api/rooms/{code}/join")
async def join_room(code: str, body: JoinRoom):
    room = get_room(code)
    try:
        player = room.add_player(body.name)
    except GameError as e:
        raise HTTPException(400, str(e)) from None
    if not player.was_online:
        # A player taking back their own offline seat is not "new"; they get
        # the "is back" pop-up when their phone connects instead.
        await notify(room, "joined", player.name, skip=player.id)
    await broadcast(room)
    return {"code": room.code, "player_id": player.id}


async def notify(room: Room, event: str, name: str, skip: str | None = None) -> None:
    """Send a one-off pop-up message (e.g. "Sam left") to everyone in the room."""
    msg = {"type": "event", "event": event, "name": name}
    for pid, ws in list(sockets.get(room.code, {}).items()):
        if pid == skip:
            continue
        try:
            await ws.send_json(msg)
        except Exception:
            pass


async def hand_over_host(room: Room) -> None:
    new_host = room.ensure_host()
    if new_host:
        await notify(room, "new_host", room.players[new_host].name)


async def watch_disconnect(room: Room, player_id: str) -> None:
    await asyncio.sleep(OFFLINE_NOTICE_SECONDS)
    player = room.players.get(player_id)
    if player is None or player.connected:
        return
    announced_offline.add((room.code, player_id))
    await notify(room, "disconnected", player.name)

    await asyncio.sleep(HOST_HANDOVER_SECONDS - OFFLINE_NOTICE_SECONDS)
    player = room.players.get(player_id)
    if player is not None and not player.connected and room.host_id == player_id:
        await hand_over_host(room)
        await broadcast(room)


async def leave(room: Room, player_id: str) -> None:
    player = room.players[player_id]
    new_host = room.remove_player(player_id)
    announced_offline.discard((room.code, player_id))
    sockets.get(room.code, {}).pop(player_id, None)
    if not room.players:
        rooms.pop(room.code, None)
        sockets.pop(room.code, None)
        return
    await notify(room, "left", player.name, skip=player_id)
    if new_host:
        await notify(room, "new_host", room.players[new_host].name)


async def broadcast(room: Room) -> None:
    now = time.time()
    for pid, ws in list(sockets.get(room.code, {}).items()):
        try:
            await ws.send_json({"type": "state", "state": room.state_for(pid, now)})
        except Exception:
            pass  # the receive loop will notice and clean up


async def expire_turn(room: Room, turn_number: int) -> None:
    await asyncio.sleep(TURN_SECONDS)
    if room.finish_turn(turn_number):
        await broadcast(room)


def handle(room: Room, player_id: str, msg: dict) -> None:
    action = msg.get("action")
    if action == "set_team":
        room.set_team(player_id, int(msg["team"]))
    elif action == "shuffle_teams":
        room.shuffle_teams(player_id)
    elif action == "start_game":
        room.start_game(player_id)
    elif action == "start_timer":
        turn = room.start_timer(player_id)
        asyncio.create_task(expire_turn(room, turn.number))
    elif action == "toggle_word":
        room.toggle_word(player_id, int(msg["index"]))
    elif action == "stop_early":
        room.stop_early(player_id)
    elif action == "next_turn":
        room.next_turn(player_id)
    else:
        raise GameError("Unknown action")


@app.websocket("/ws/{code}/{player_id}")
async def websocket_endpoint(ws: WebSocket, code: str, player_id: str):
    room = rooms.get(code.upper())
    await ws.accept()
    if room is None or player_id not in room.players:
        await ws.send_json({"type": "gone"})
        await ws.close()
        return

    conns = sockets.setdefault(room.code, {})
    old = conns.get(player_id)
    if old is not None:  # same player reconnected (e.g. phone screen locked)
        try:
            await old.close()
        except Exception:
            pass
    conns[player_id] = ws
    player = room.players[player_id]
    player.connected = player.was_online = True
    if (room.code, player_id) in announced_offline:
        announced_offline.discard((room.code, player_id))
        await notify(room, "reconnected", player.name, skip=player_id)
    # If the host vanished while nobody else was online, take over now.
    host = room.players.get(room.host_id)
    if host is None or (not host.connected and (room.code, host.id) in announced_offline):
        await hand_over_host(room)
    await broadcast(room)

    try:
        while True:
            msg = await ws.receive_json()
            room.touch()
            if msg.get("action") == "ping":
                # Heartbeat from the phone: keeps the connection (and a
                # Serverless app) awake during quiet moments in a game.
                await ws.send_json({"type": "pong"})
                continue
            if msg.get("action") == "leave":
                await leave(room, player_id)
                await broadcast(room)
                await ws.close()
                return
            try:
                handle(room, player_id, msg)
            except (GameError, KeyError, ValueError, TypeError) as e:
                await ws.send_json({"type": "error", "message": str(e)})
                continue
            await broadcast(room)
    except WebSocketDisconnect:
        pass
    finally:
        if conns.get(player_id) is ws:
            del conns[player_id]
            if player_id in room.players:
                room.players[player_id].connected = False
                asyncio.create_task(watch_disconnect(room, player_id))
                await broadcast(room)


@app.get("/healthz")
def healthz():
    return {"ok": True, "rooms": len(rooms)}


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

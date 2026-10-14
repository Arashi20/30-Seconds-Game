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

app = FastAPI(title="30 Seconds")
rooms: dict[str, Room] = {}
# room code -> {player_id: websocket}
sockets: dict[str, dict[str, WebSocket]] = {}


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
    await broadcast(room)
    return {"code": room.code, "player_id": player.id}


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
    room.players[player_id].connected = True
    await broadcast(room)

    try:
        while True:
            msg = await ws.receive_json()
            room.touch()
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
            room.players[player_id].connected = False
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

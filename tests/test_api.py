"""End-to-end test: create a room, four players join over WebSockets, play a turn."""

import asyncio
import json
import time
from contextlib import contextmanager

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app, rooms

client = TestClient(app)


def receive_state(ws):
    while True:
        msg = ws.receive_json()
        if msg["type"] == "state":
            return msg["state"]
        if msg["type"] == "error":
            raise AssertionError(msg["message"])


def drain(ws, predicate):
    """Read state messages until one matches (broadcasts can arrive in bursts)."""
    for _ in range(50):
        state = receive_state(ws)
        if predicate(state):
            return state
    raise AssertionError("expected state never arrived")


def test_index_and_health():
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/healthz").json()["ok"] is True


def test_join_unknown_room_and_bad_settings():
    assert client.post("/api/rooms/ZZZZ/join", json={"name": "x"}).status_code == 404
    assert client.post("/api/rooms", json={"name": "x", "lang": "de"}).status_code == 400
    assert client.post("/api/rooms", json={"name": "x", "teams": 9}).status_code == 400


def test_full_turn_over_websockets():
    res = client.post("/api/rooms", json={"name": "Host", "lang": "nl"}).json()
    code, host = res["code"], res["player_id"]
    others = [client.post(f"/api/rooms/{code.lower()}/join", json={"name": n}).json()["player_id"] for n in ("A", "B", "C")]
    ids = [host, *others]

    sockets = {pid: client.websocket_connect(f"/ws/{code}/{pid}").__enter__() for pid in ids}
    try:
        state = drain(sockets[host], lambda s: all(p["connected"] for p in s["players"]) and len(s["players"]) == 4)
        assert state["phase"] == "lobby"

        sockets[host].send_json({"action": "start_game"})
        state = drain(sockets[host], lambda s: s["phase"] == "playing")
        describer = state["turn"]["describer_id"]

        sockets[describer].send_json({"action": "start_timer"})
        state = drain(sockets[describer], lambda s: s["turn"]["phase"] == "running")
        assert len(state["turn"]["words"]) == 5
        assert 0 < state["turn"]["remaining"] <= 30

        sockets[describer].send_json({"action": "toggle_word", "index": 0})
        sockets[describer].send_json({"action": "toggle_word", "index": 1})
        sockets[describer].send_json({"action": "stop_early"})
        state = drain(sockets[describer], lambda s: s["turn"]["phase"] == "review")
        turn_score = state["turn"]["score"]
        assert turn_score == max(0, 2 - state["turn"]["die"])

        sockets[describer].send_json({"action": "next_turn"})
        state = drain(sockets[describer], lambda s: s["turn"]["number"] == 2)
        assert sum(state["positions"]) == turn_score
        assert code in rooms

        # Invalid action yields an error message, not a disconnect.
        sockets[host].send_json({"action": "bogus"})
        while True:
            msg = sockets[host].receive_json()
            if msg["type"] == "error":
                break
    finally:
        for ws in sockets.values():
            ws.__exit__(None, None, None)


def test_unknown_player_socket_is_told_room_is_gone():
    with client.websocket_connect("/ws/ABCD/nobody") as ws:
        assert ws.receive_json()["type"] == "gone"


def test_timer_runs_out_by_itself(monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "TURN_SECONDS", 0.3)
    res = client.post("/api/rooms", json={"name": "H", "lang": "en"}).json()
    code, host = res["code"], res["player_id"]
    for n in ("A", "B", "C"):
        client.post(f"/api/rooms/{code}/join", json={"name": n})
    room = rooms[code]
    room.start_game(host)
    describer = room.turn.describer_id

    with client.websocket_connect(f"/ws/{code}/{describer}") as ws:
        receive_state(ws)
        ws.send_json({"action": "start_timer"})
        state = drain(ws, lambda s: s["turn"]["phase"] == "review")
        assert state["turn"]["remaining"] is None


def receive_event(ws, event):
    for _ in range(50):
        msg = ws.receive_json()
        if msg["type"] == "event" and msg["event"] == event:
            return msg
    raise AssertionError(f"no {event} event")


def test_leave_notifies_others_and_hands_over_host():
    res = client.post("/api/rooms", json={"name": "Host", "lang": "en"}).json()
    code, host = res["code"], res["player_id"]
    bob = client.post(f"/api/rooms/{code}/join", json={"name": "Bob"}).json()["player_id"]

    with client.websocket_connect(f"/ws/{code}/{bob}") as bob_ws:
        with client.websocket_connect(f"/ws/{code}/{host}") as host_ws:
            receive_state(host_ws)
            host_ws.send_json({"action": "leave"})
        assert receive_event(bob_ws, "left")["name"] == "Host"
        assert receive_event(bob_ws, "new_host")["name"] == "Bob"
        state = drain(bob_ws, lambda s: len(s["players"]) == 1)
        assert state["host_id"] == bob
    assert host not in rooms[code].players


@pytest.fixture
def live_server(monkeypatch):
    """A real uvicorn server in a thread. Needed for disconnects: the TestClient
    runs every WebSocket in its own short-lived event loop, which cancels the
    background tasks a dropped connection starts."""
    import socket
    import threading

    import uvicorn

    import app.main as main

    monkeypatch.setattr(main, "OFFLINE_NOTICE_SECONDS", 0.1)
    monkeypatch.setattr(main, "HOST_HANDOVER_SECONDS", 0.3)
    monkeypatch.setattr(main, "IDLE_CHECK_SECONDS", 0.1)
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    while not server.started:
        time.sleep(0.01)
    yield f"127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=5)


class LiveSocket:
    """Gives a websockets connection the same receive_json() as the TestClient."""

    def __init__(self, ws):
        self.ws = ws

    def receive_json(self, timeout=5):
        return json.loads(self.ws.recv(timeout=timeout))

    def pending(self):
        """Everything received so far, without waiting for more."""
        from websockets.exceptions import ConnectionClosed

        msgs = []
        while True:
            try:
                msgs.append(self.receive_json(timeout=0.2))
            except (TimeoutError, ConnectionClosed):
                return msgs


@contextmanager
def live_socket(url):
    from websockets.sync.client import connect

    with connect(url, open_timeout=5) as ws:
        yield LiveSocket(ws)


def live_room(live_server):
    http = httpx.Client(base_url=f"http://{live_server}")
    res = http.post("/api/rooms", json={"name": "Host", "lang": "en"}).json()
    code, host = res["code"], res["player_id"]
    bob = http.post(f"/api/rooms/{code}/join", json={"name": "Bob"}).json()["player_id"]
    return f"ws://{live_server}/ws/{code}", host, bob


def test_disconnected_host_is_announced_and_replaced(live_server):
    base, host, bob = live_room(live_server)
    with live_socket(f"{base}/{bob}") as bob_ws:
        with live_socket(f"{base}/{host}") as host_ws:
            receive_state(host_ws)
        # host's connection dropped (not a deliberate leave)
        assert receive_event(bob_ws, "disconnected")["name"] == "Host"
        assert receive_event(bob_ws, "new_host")["name"] == "Bob"
        assert drain(bob_ws, lambda s: s["host_id"] == bob)

        with live_socket(f"{base}/{host}") as host_ws:
            assert receive_event(bob_ws, "reconnected")["name"] == "Host"
            assert receive_state(host_ws)["host_id"] == bob  # Bob stays host


def test_quick_reconnect_is_not_announced(live_server):
    base, host, bob = live_room(live_server)
    with live_socket(f"{base}/{host}") as host_ws:
        with live_socket(f"{base}/{bob}") as bob_ws:
            receive_state(bob_ws)
        with live_socket(f"{base}/{bob}") as bob_ws:  # back within the grace period
            time.sleep(0.5)  # well past the (patched) notice delay
            events = [m["event"] for m in host_ws.pending() if m["type"] == "event"]
            assert "disconnected" not in events
            assert "reconnected" not in events


def test_ping_gets_pong_without_broadcasting():
    res = client.post("/api/rooms", json={"name": "Host", "lang": "en"}).json()
    code, host = res["code"], res["player_id"]
    with client.websocket_connect(f"/ws/{code}/{host}") as ws:
        receive_state(ws)
        ws.send_json({"action": "ping"})
        assert ws.receive_json() == {"type": "pong"}  # nothing else in between


def test_page_and_assets_are_always_revalidated():
    for path in ("/", "/static/app.js", "/static/style.css", "/static/logo.svg"):
        res = client.get(path)
        assert res.status_code == 200
        assert res.headers["cache-control"] == "no-cache"
        assert "etag" in res.headers or "last-modified" in res.headers
    etag = client.get("/static/app.js").headers["etag"]
    assert client.get("/static/app.js", headers={"If-None-Match": etag}).status_code == 304
    assert "cache-control" not in client.get("/healthz").headers


def test_create_needs_password_only_when_set(monkeypatch):
    monkeypatch.delenv("CREATE_PASSWORD", raising=False)
    assert client.get("/api/config").json() == {"needs_password": False}
    assert client.post("/api/rooms", json={"name": "A"}).status_code == 200

    monkeypatch.setenv("CREATE_PASSWORD", "spelavond")
    assert client.get("/api/config").json() == {"needs_password": True}
    assert client.post("/api/rooms", json={"name": "A"}).status_code == 403
    assert client.post("/api/rooms", json={"name": "A", "password": "nope"}).status_code == 403
    res = client.post("/api/rooms", json={"name": "A", "password": "spelavond"})
    assert res.status_code == 200

    # Joining never needs the password.
    assert client.post(f"/api/rooms/{res.json()['code']}/join", json={"name": "B"}).status_code == 200


def test_idle_room_is_closed_even_with_heartbeats(live_server, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "IDLE_CLOSE_SECONDS", 1.0)
    base, host, bob = live_room(live_server)
    code = base.rsplit("/", 1)[-1]
    with live_socket(f"{base}/{host}") as ws:
        receive_state(ws)
        closed = None
        for _ in range(20):  # a forgotten tab: only heartbeats, no real actions
            ws.ws.send(json.dumps({"action": "ping"}))
            closed = next((m for m in ws.pending() if m["type"] == "closed"), None)
            if closed:
                break
        assert closed is not None  # closed by the server's own background sweep
    assert code not in rooms


def test_active_room_is_not_closed(monkeypatch):
    import app.main as main

    res = client.post("/api/rooms", json={"name": "Host", "lang": "en"}).json()
    monkeypatch.setattr(main, "IDLE_CLOSE_SECONDS", 60)
    asyncio.run(main.close_idle_rooms())
    assert res["code"] in rooms

"""End-to-end test: create a room, four players join over WebSockets, play a turn."""

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

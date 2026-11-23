from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_config():
    r = client.get("/api/config").json()
    assert len(r["scenarios"]) == 5 and r["config"]["dt"] == 5


def test_policy_and_solve():
    r = client.get("/api/policy", params={"scenario": "S3"}).json()
    assert len(r["states"]) == 96 and r["vi_equals_pi"] is True
    r2 = client.post("/api/solve", json={"lam_ns": 0.2, "lam_ew": 0.2, "gamma": 0.9,
                                         "c_switch": 5}).json()
    assert r2["params"]["gamma"] == 0.9 and r2["params"]["c_switch"] == 5
    assert client.post("/api/solve", json={"gamma": 1.5}).status_code == 422
    assert client.get("/api/policy", params={"scenario": "nope"}).status_code == 404


def test_websocket_stream_runs_to_completion():
    with client.websocket_connect("/ws/sim") as ws:
        ws.send_json({"type": "start", "scenario": "S2", "seed": 1,
                      "controllers": ["mdp", "fixed"], "speed": 500})
        init = ws.receive_json()
        assert init["type"] == "init" and init["controllers"] == ["mdp", "fixed"]
        frames, last = 0, None
        while True:
            m = ws.receive_json()
            if m["type"] == "done":
                last = m
                break
            frames += 1
            assert m["type"] == "frame"
            assert set(m["controllers"]) == {"mdp", "fixed"}
            c = m["controllers"]["mdp"]
            assert len(c["ticks"]) == 5 and len(c["state"]) == 4
        assert frames == 720
        # same arrival stream -> same number of arrivals for both controllers
        s = last["summary"]
        assert s["mdp"]["arrived"] == s["fixed"]["arrived"]


def test_websocket_pause_and_lambda():
    with client.websocket_connect("/ws/sim") as ws:
        ws.send_json({"type": "start", "scenario": "S1", "seed": 2,
                      "controllers": ["mdp"], "speed": 20})
        ws.receive_json()
        ws.receive_json()  # first frame
        ws.send_json({"type": "set_lambda", "lam_ns": 0.3, "lam_ew": 0.05})
        for _ in range(4):
            m = ws.receive_json()
        assert m["type"] == "frame"
        assert m["lam"] == [0.3, 0.05]
        ws.send_json({"type": "stop"})

"""Pause/resume/stop control for the input agent (UI Pause button)."""
import threading
import time

from input_agent import ExecControl


def test_runs_by_default():
    c = ExecControl()
    c.reset(5)
    assert c.proceed() is True
    assert c.status() == {"paused": False, "stopped": False, "placed": 0, "total": 5}


def test_pause_blocks_until_resume():
    c = ExecControl()
    c.reset(1)
    c.pause()
    results = []
    t = threading.Thread(target=lambda: results.append(c.proceed()))
    t.start()
    time.sleep(0.15)
    assert not results, "proceed() should block while paused"
    assert c.status()["paused"] is True
    c.resume()
    t.join(timeout=2)
    assert results == [True]


def test_stop_unblocks_a_paused_loop():
    c = ExecControl()
    c.reset(1)
    c.pause()
    results = []
    t = threading.Thread(target=lambda: results.append(c.proceed()))
    t.start()
    c.stop()
    t.join(timeout=2)
    assert results == [False], "stop must release the pause and end the loop"
    assert c.status()["stopped"] is True


def test_reset_rearms_after_stop():
    c = ExecControl()
    c.stop()
    c.reset(3)
    assert c.proceed() is True
    assert c.status() == {"paused": False, "stopped": False, "placed": 0, "total": 3}


def test_control_endpoints():
    from app import app

    client = app.test_client()
    r = client.post("/execute_control", json={"action": "pause"})
    assert r.status_code == 200 and r.get_json()["paused"] is True
    r = client.post("/execute_control", json={"action": "resume"})
    assert r.get_json()["paused"] is False
    r = client.post("/execute_control", json={"action": "stop"})
    assert r.get_json()["stopped"] is True
    assert client.post("/execute_control", json={"action": "nope"}).status_code == 400
    assert client.get("/execute_status").status_code == 200

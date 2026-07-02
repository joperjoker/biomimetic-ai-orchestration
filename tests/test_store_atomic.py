"""Tests for the SQLite coordination store, especially the atomic claim."""

import threading

from cta.store import Store


def test_schema_and_basic_task_lifecycle(tmp_path):
    store = Store(tmp_path / "cta.db")
    store.init_schema()
    store.add_task("t1", {"domain": "coding"})
    store.advertise("t1")
    task = store.get_task("t1")
    assert task is not None
    assert task["status"] == "ADVERTISED"
    assert [t["task_id"] for t in store.advertised_tasks()] == ["t1"]


def test_claim_on_non_advertised_fails(tmp_path):
    store = Store(tmp_path / "cta.db")
    store.init_schema()
    store.add_task("t1", {})  # left in CREATED, never advertised
    assert store.claim("t1", "agent0") is False
    assert store.get_task("t1")["status"] == "CREATED"


def test_atomic_claim_exactly_one_winner(tmp_path):
    store = Store(tmp_path / "cta.db")
    store.init_schema()
    store.add_task("hot", {"domain": "coding"})
    store.advertise("hot")

    n = 32
    winners: list[str] = []
    lock = threading.Lock()
    barrier = threading.Barrier(n)

    def worker(i: int) -> None:
        agent = f"agent{i}"
        barrier.wait()  # release all threads together to maximise contention
        if store.claim("hot", agent):
            with lock:
                winners.append(agent)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(winners) == 1, f"expected exactly one winner, got {winners}"
    task = store.get_task("hot")
    assert task["status"] == "CLAIMED"
    assert task["claimed_by"] == winners[0]


def test_events_and_reliability(tmp_path):
    store = Store(tmp_path / "cta.db")
    store.init_schema()
    store.append_event("ADVERTISE", task_id="t1")
    store.append_event("CLAIM_WIN", task_id="t1", agent_id="a1")
    assert store.event_count() == 2
    assert store.event_count("CLAIM_WIN") == 1

    # A new agent starts at 0.5; a strong record moves reliability up.
    assert store.reliability("new") == 0.5
    for _ in range(9):
        store.record_attempt("a1", success=True)
    store.record_attempt("a1", success=False)
    r = store.reliability("a1")
    assert 0.7 < r < 0.95

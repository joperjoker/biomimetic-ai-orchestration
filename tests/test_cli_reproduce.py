"""The reproduce-all command is wired to the full deterministic pipeline."""

import cta.cli as cli


def test_reproduce_all_runs_the_full_protocol(monkeypatch, capsys):
    calls = {}

    def fake_autorun(out_dir, demo=True, protocol=None):
        calls["out"] = out_dir
        calls["demo"] = demo
        return {"verdicts": {"H1": {"verdict": "SUPPORTED"}}}

    monkeypatch.setattr(cli, "autorun", fake_autorun)
    rc = cli.main(["reproduce-all", "--out", "somewhere"])
    assert rc == 0
    # It regenerates into the given directory and uses the full (not demo) protocol.
    assert calls == {"out": "somewhere", "demo": False}
    assert "reproduce-all complete" in capsys.readouterr().out

from __future__ import annotations

from cozinha import __main__ as principal
from cozinha.config import Config


def test_main_args(monkeypatch):
    recebidas: list[Config] = []
    monkeypatch.setattr("cozinha.ui.app.rodar", recebidas.append)
    principal.main([])
    principal.main(["--demo-deadlock"])
    assert recebidas[0] == Config()
    assert recebidas[1] == Config.demo_deadlock()

from __future__ import annotations

import ast
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent / "cozinha"


def _importa_pygame(arquivo: Path) -> bool:
    arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Import):
            nomes = [a.name for a in no.names]
        elif isinstance(no, ast.ImportFrom):
            nomes = [no.module or ""]
        else:
            continue
        if any(n == "pygame" or n.startswith("pygame.") for n in nomes):
            return True
    return False


def test_so_ui_importa_pygame():
    culpados = []
    for arquivo in RAIZ.rglob("*.py"):
        rel = arquivo.relative_to(RAIZ)
        if rel.parts[0] == "ui" or rel == Path("__main__.py"):
            continue
        if _importa_pygame(arquivo):
            culpados.append(str(rel))
    assert not culpados, f"importam pygame fora de cozinha/ui: {culpados}"


def test_detecta_import_de_pygame(tmp_path):
    arquivo = tmp_path / "x.py"
    arquivo.write_text("from pygame.locals import QUIT\n", encoding="utf-8")
    assert _importa_pygame(arquivo)


@pytest.mark.demo
def test_demo_fica_fora():
    """Só roda com `pytest -m demo`: prova que o marcador separa as demos."""

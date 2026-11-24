"""python -m cozinha [--demo-deadlock]"""
from __future__ import annotations

import argparse
import logging

from cozinha.config import Config


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m cozinha",
                                     description="Cozinha Concorrente: jogo de cozinha com threads.")
    parser.add_argument("--demo-deadlock", action="store_true",
                        help="cozinha sem a ordem fixa de aquisição, para mostrar o deadlock")
    args = parser.parse_args(argv)
    if args.demo_deadlock:
        config = Config.demo_deadlock()
    else:
        config = Config.single_player()        # você é o cozinheiro 1; o nível muda na tela
        config.validar_para_jogo()
    logging.basicConfig(level=logging.WARNING)
    from cozinha.ui import app                      # só aqui o pygame entra
    app.rodar(config)


if __name__ == "__main__":
    main()

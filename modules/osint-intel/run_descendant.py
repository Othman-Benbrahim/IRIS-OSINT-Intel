#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_descendant.py — Orchestrateur du mode descendant (CLI).

Chaîne inverse : rapport IRIS/Yggdrasil → re-challenge OSINT → rapport-osint.md
référençant la session source et ses divergences.

    python run_descendant.py entree-iris.md --llm ollama --out rapport-rechallenge.md
    python run_descendant.py entree-iris.md --demo --fixtures --out rapport-rechallenge.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for p in (_HERE, _HERE / "deep-research"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import mode_descendant            # noqa: E402
from run_analyse import _llm_demo  # noqa: E402


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Mode descendant : rapport IRIS → re-challenge")
    p.add_argument("entree", help="rapport entrant (source iris-station|yggdrasil)")
    p.add_argument("--out", default="rapport-rechallenge.md")
    p.add_argument("--llm", choices=["ollama", "fantasyai"], default=None)
    p.add_argument("--demo", action="store_true", help="faux LLM intégré (test)")
    p.add_argument("--fixtures", action="store_true", help="deep research sur données en dur")
    args = p.parse_args(argv)

    if args.demo:
        llm = _llm_demo()
    elif args.llm == "ollama":
        import llm_adapters
        llm = llm_adapters.adaptateur_ollama()
    elif args.llm == "fantasyai":
        import os
        import llm_adapters
        llm = llm_adapters.adaptateur_fantasyai(
            url=os.environ.get("FANTASYAI_URL", ""), cle=os.environ.get("FANTASYAI_CLE", ""))
    else:
        print("⛔ Le re-challenge requiert un LLM (--llm ollama|fantasyai ou --demo).",
              file=sys.stderr)
        return 2

    fixtures = None
    if args.fixtures:
        import fixtures as fx
        fixtures = fx.FIXTURES_CRISE_EMERGENTS

    try:
        chemin = mode_descendant.re_challenger_fichier(
            args.entree, args.out, llm, fixtures=fixtures)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    print(f"✅ Rapport de re-challenge écrit et validé : {chemin}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

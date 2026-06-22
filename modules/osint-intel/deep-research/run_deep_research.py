#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_deep_research.py — Orchestrateur Deep Research (CLI).

Chaîne complète : question → collecte (search) → synthèse (synthesizer) → corpus.md

Exemples :
    # Avec réseau + LLM Ollama local :
    python run_deep_research.py "crise financière émergents 2027" --llm ollama --out corpus.md

    # Sans réseau ni LLM, sur fixtures (test) :
    python run_deep_research.py "crise financière émergents 2027" --fixtures --out corpus.md

    # Collecte web mais synthèse extractive (sans LLM) :
    python run_deep_research.py "ma question" --out corpus.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Le dossier du script est sur sys.path[0] : imports plats possibles.
import search
import synthesizer


def _choisir_llm(nom: str | None):
    if not nom:
        return None
    import llm_adapters
    if nom == "ollama":
        return llm_adapters.adaptateur_ollama()
    if nom == "fantasyai":
        # À configurer : variables d'environnement FANTASYAI_URL / FANTASYAI_CLE
        import os
        return llm_adapters.adaptateur_fantasyai(
            url=os.environ.get("FANTASYAI_URL", ""),
            cle=os.environ.get("FANTASYAI_CLE", ""),
        )
    raise SystemExit(f"LLM inconnu : {nom} (attendu : ollama | fantasyai)")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Deep Research : question → corpus.md")
    p.add_argument("question", help="question d'intelligence")
    p.add_argument("--out", default="corpus.md", help="fichier de sortie")
    p.add_argument("--fixtures", action="store_true",
                   help="utilise des résultats en dur (test hors-réseau)")
    p.add_argument("--hors-ligne", action="store_true",
                   help="saute les backends web")
    p.add_argument("--llm", choices=["ollama", "fantasyai"], default=None,
                   help="adaptateur LLM pour la synthèse (sinon : extractif)")
    args = p.parse_args(argv)

    fixtures = None
    if args.fixtures:
        import fixtures as fx
        fixtures = fx.FIXTURES_CRISE_EMERGENTS

    collecte = search.collecter(
        args.question,
        fixtures=fixtures,
        forcer_hors_ligne=args.hors_ligne,
    )

    if collecte["hors_ligne"] and not args.fixtures:
        print("⚠  Hors-ligne : Deep Research nécessite une connexion. "
              "Backends web sautés.", file=sys.stderr)

    llm = _choisir_llm(args.llm)
    corpus = synthesizer.synthetiser(collecte, llm=llm)
    md = synthesizer.corpus_vers_md(collecte, corpus)
    Path(args.out).write_text(md, encoding="utf-8")

    print(f"✅ Corpus écrit : {args.out}")
    print(f"   collecte={collecte['mode_collecte']} · synthèse={corpus['mode_synthese']} "
          f"· {len(corpus['assertions'])} assertion(s) "
          f"· fiabilité globale {corpus['fiabilite_globale']}/5")
    if collecte["inaccessibles"]:
        print(f"   {len(collecte['inaccessibles'])} source(s) inaccessible(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

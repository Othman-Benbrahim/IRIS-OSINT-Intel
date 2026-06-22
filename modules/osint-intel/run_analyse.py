#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_analyse.py — Orchestrateur d'analyse (CLI).

Chaîne : corpus-valide.md → [VERROU de validation] → analyse terrain → export →
rapport-osint.md (validé contre le contrat d'échange).

    python run_analyse.py corpus-valide.md --llm ollama --out rapport-osint.md
    python run_analyse.py corpus-valide.md --demo --out rapport-osint.md   # faux LLM (test)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
for p in (_HERE, _HERE / "validation", _HERE / "deep-research"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import analyse           # noqa: E402
import export            # noqa: E402
import validation_gate as vg  # noqa: E402


def _llm_demo():
    """Faux LLM déterministe pour tester la chaîne sans backend réel."""
    reponse = json.dumps({
        "hypotheses": [
            {"name": "Crise systémique par défaut souverain en chaîne",
             "probability_prior": 0.25, "type": "dominante"},
            {"name": "Correction ordonnée avec intervention multilatérale",
             "probability_prior": 0.45, "type": "dissidente"},
            {"name": "Évitement par croissance surprise des émergents",
             "probability_prior": 0.20, "type": "fractale"},
        ],
        "scenarios": [
            {"name": "Crise aiguë généralisée", "probability": 0.15,
             "indicators": ["Spread EMBI > 800bps", "≥2 défauts souverains"]},
            {"name": "Correction ordonnée FMI", "probability": 0.55,
             "indicators": ["Accord préventif FMI", "Coordination G20"]},
            {"name": "Stagflation sans crise", "probability": 0.30,
             "indicators": ["Croissance mondiale < 2%"]},
        ],
        "predictions": [
            {"question": "Spread EMBI Global < 600bps au 31/12/2026 ?",
             "probability": 0.65, "type": "binaire", "horizon": "2026-12-31",
             "indicators": ["JPMorgan EMBI Global"]},
            {"question": "Au moins un défaut souverain déclaré en 2026 ?",
             "probability": 0.30, "type": "binaire", "horizon": "2026-12-31",
             "indicators": ["Annonces S&P/Moody's"]},
        ],
        "signaux_faibles": [
            {"signal": "Doublement des swaps de devises Chine-émergents",
             "direction": "↑", "significance": "haute"},
        ],
        "biais_detectes": [
            {"biais": "Ancrage sur la crise de 2008",
             "correction": "Élargir le base rate à 1990-2026"},
        ],
        "lacunes": ["Réserves de change par pays (Q2 2026) non couvertes"],
        "signaux_a_surveiller": ["Lignes de swap Fed", "Dégradation S&P d'un poids lourd émergent"],
        "risque": "Risque modéré et conditionnel : ordonné si coordination multilatérale, "
                  "aigu en cas de défaut isolé non contenu.",
        "recommandations": ["Surveiller les communiqués FMI/G20",
                            "Transmettre à IRIS-Station pour formalisation ACH"],
    }, ensure_ascii=False)
    return lambda _prompt: reponse


def _choisir_llm(nom, demo):
    if demo:
        return _llm_demo()
    if not nom:
        return None
    import llm_adapters
    if nom == "ollama":
        return llm_adapters.adaptateur_ollama()
    if nom == "fantasyai":
        import os
        return llm_adapters.adaptateur_fantasyai(
            url=os.environ.get("FANTASYAI_URL", ""),
            cle=os.environ.get("FANTASYAI_CLE", ""))
    raise SystemExit(f"LLM inconnu : {nom}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Analyse terrain → rapport-osint.md")
    p.add_argument("corpus", help="corpus-valide.md (issu de la Phase 3)")
    p.add_argument("--out", default="rapport-osint.md")
    p.add_argument("--llm", choices=["ollama", "fantasyai"], default=None)
    p.add_argument("--demo", action="store_true", help="faux LLM intégré (test)")
    p.add_argument("--strict", action="store_true", help="avertissements = erreurs")
    args = p.parse_args(argv)

    corpus = vg.charger_corpus(args.corpus)

    # VERROU : rien n'est analysé sans validation (Phase 3)
    try:
        vg.exiger_validation(corpus)
    except PermissionError as e:
        print(f"⛔ {e}", file=sys.stderr)
        return 2

    llm = _choisir_llm(args.llm, args.demo)
    resultat = analyse.analyser(corpus, llm=llm)
    try:
        chemin = export.exporter(resultat, args.out, strict=args.strict)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1

    print(f"✅ Rapport écrit et validé : {chemin}")
    print(f"   {len(resultat['hypotheses'])} hypothèses · "
          f"{len(resultat['scenarios'])} scénarios · "
          f"{len(resultat['predictions'])} prédictions · "
          f"{resultat['sources_stats']['total']} sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())

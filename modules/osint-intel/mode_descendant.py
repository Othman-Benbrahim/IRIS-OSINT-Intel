#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mode_descendant.py — Flux inverse (Phase 5).

OSINT-Intel reprend un rapport IRIS-Station ou Yggdrasil et le RE-CHALLENGE :
  1. lit le bloc `a_osint_intel` (action, focus, questions) ;
  2. relance un deep research systématique sur ces questions ;
  3. confronte au graphe source : entités/signaux ABSENTS du graphe d'origine ;
  4. réévalue les hypothèses formalisées à la lumière des nouvelles sources ;
  5. exporte un rapport OSINT référençant la session source + ses divergences.

Réutilise search (Phase 2), synthesizer (Phase 2), analyse + export (Phase 4).
Le rapport produit reste conforme au contrat d'échange (Phase 1).
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_RACINE = _HERE.parents[1]
for p in (_HERE, _HERE / "deep-research", str(_RACINE)):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import analyse           # noqa: E402
import export            # noqa: E402
import search            # noqa: E402
import synthesizer       # noqa: E402
from shared import exchange_format as xf  # noqa: E402


def charger_entree(source) -> dict:
    """Charge et valide un rapport entrant (source iris-station|yggdrasil)."""
    doc = xf.charger(source)
    rapport = xf.valider(doc)
    ex = doc.get("iris_exchange", {})
    if ex.get("source") not in xf.SOURCES_ENTREE:
        raise ValueError(
            f"Entrée attendue de {sorted(xf.SOURCES_ENTREE)}, reçu : {ex.get('source')!r}"
        )
    if not rapport.ok:
        details = "; ".join(f"{c}: {m}" for c, m in rapport.erreurs)
        raise ValueError(f"Rapport entrant non conforme : {details}")
    return ex


def _entites_graphe_source(ex: dict) -> set[str]:
    return {e.lower() for e in (ex.get("graphe", {}) or {}).get("entites_top", [])}


def challenger(entree: dict, llm, fixtures=None, forcer_hors_ligne=False) -> tuple[dict, dict]:
    """Re-challenge. Renvoie (analyse_rechallenge, reference_source)."""
    aoi = entree.get("a_osint_intel", {}) or {}
    questions = aoi.get("questions") or [entree.get("question", "")]
    focus = aoi.get("focus", [])

    # Deep research systématique sur les questions de challenge
    resultats, requetes = [], []
    for q in questions:
        col = search.collecter(q, fixtures=fixtures, forcer_hors_ligne=forcer_hors_ligne)
        resultats.extend(col["resultats"])
        requetes.extend(col["requetes"])
    collecte = {"question": entree.get("question", "; ".join(questions)),
                "horodatage": search.datetime.now(search.timezone.utc).isoformat(timespec="seconds"),
                "mode_collecte": "fixtures" if fixtures else "reseau",
                "hors_ligne": forcer_hors_ligne, "parse": {}, "requetes": requetes,
                "backends_actifs": [], "resultats": resultats, "inaccessibles": []}

    corpus = synthesizer.synthetiser(collecte, llm=None)  # synthèse extractive du nouveau corpus

    # Le re-challenge analytique est de l'inférence -> on (ré)analyse avec le LLM,
    # en injectant le corpus comme « validé » (flux automatique du mode descendant)
    corpus["validation"] = {"valide": True, "par": "mode_descendant"}
    resultat = analyse.analyser(corpus, llm=llm)

    # Confrontation au graphe source : entités nouvelles (absentes du graphe d'origine)
    graphe_src = _entites_graphe_source(entree)
    entites_nouvelles = [e["nom"] for e in resultat.get("entites_cles", [])
                         if e.get("nom") and e["nom"].lower() not in graphe_src]

    reference_source = {
        "reference_source": {
            "session_id": entree.get("session_id"),
            "source": entree.get("source"),
            "action": aoi.get("action", "challenger"),
            "focus": focus,
            "entites_absentes_du_graphe": entites_nouvelles,
            "signaux_non_captures": [s.get("signal") for s in resultat.get("signaux_faibles", [])],
            "hypotheses_rechallengees": [
                {"id": h.get("id"), "p_h_e_iris": h.get("p_h_e"), "name": h.get("name")}
                for h in entree.get("hypotheses_formalisees", [])
            ],
        }
    }
    return resultat, reference_source


def re_challenger_fichier(chemin_entree, chemin_sortie, llm,
                          fixtures=None, forcer_hors_ligne=False) -> str:
    entree = charger_entree(chemin_entree)
    resultat, ref = challenger(entree, llm, fixtures, forcer_hors_ligne)
    # On lie les lacunes au challenge et on exporte (validé contre le contrat)
    resultat["lacunes"] = (resultat.get("lacunes", [])
                           + [f"Re-challenge de la session source {entree.get('session_id')}"])
    return export.exporter(resultat, chemin_sortie, extra=ref)

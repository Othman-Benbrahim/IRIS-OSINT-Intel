#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
export.py — Génération du rapport-osint.md (Phase 4).

Assemble le bloc YAML front matter au format d'échange IRIS∞ à partir de l'analyse
terrain, le VALIDE via shared/exchange_format.py, puis écrit le rapport.

Garde-fou : aucun rapport non conforme ne sort. Si la validation échoue, on lève
avec la liste des erreurs — rien n'est écrit.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# shared/ est à la racine du projet (osint-intel -> modules -> RACINE)
_RACINE = Path(__file__).resolve().parents[2]
if str(_RACINE) not in sys.path:
    sys.path.insert(0, str(_RACINE))
from shared import exchange_format as xf  # noqa: E402


def _session_id() -> str:
    return "OSINT-" + datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")


def construire_echange(analyse: dict) -> dict:
    """Construit le dict iris_exchange (format de sortie OSINT-Intel)."""
    return {
        "iris_exchange": {
            "version": xf.SCHEMA_VERSION,
            "source": "osint-intel",
            "source_version": "2.0",
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "session_id": _session_id(),
            "question_intelligence": analyse["question"],
            "mode": analyse.get("mode", "complet"),
            "deep_research_used": bool(analyse.get("deep_research_used", True)),
            "hypotheses": analyse["hypotheses"],
            "scenarios": analyse["scenarios"],
            "predictions": analyse["predictions"],
            "signaux_faibles": analyse.get("signaux_faibles", []),
            "sources": analyse["sources_stats"],
            "entites_cles": analyse.get("entites_cles", []),
            "biais_detectes": analyse.get("biais_detectes", []),
            "lacunes": analyse.get("lacunes", []),
            "signaux_a_surveiller": analyse.get("signaux_a_surveiller", []),
            "pour_iris_station": {
                "hypotheses_a_formaliser": [h["id"] for h in analyse["hypotheses"]],
                "predictions_a_scorer": [p["id"] for p in analyse["predictions"]],
                "calibration_attendue": "Formalisation ACH + calibration agrégée → IRIS-Station",
            },
        }
    }


def _corps_markdown(analyse: dict, ex: dict) -> str:
    s = ex["iris_exchange"]
    L = [f"# Rapport OSINT-Intel — {analyse['question']}", ""]
    L.append(f"_Session {s['session_id']} · mode {s['mode']} · "
             f"{analyse['sources_stats']['total']} source(s) · "
             f"fiabilité {analyse['sources_stats']['fiabilite_moyenne']}/5_")

    L.append("\n## Hypothèses concurrentes (priors intuitifs — niveau terrain)")
    for h in analyse["hypotheses"]:
        L.append(f"- **{h['id']}** ({h['type']}, prior {h['probability_prior']}) — {h['name']}")

    L.append("\n## Scénarios")
    for sc in analyse["scenarios"]:
        ind = " · ".join(sc.get("indicators", []))
        L.append(f"- **{sc['id']}** (p={sc['probability']}) — {sc['name']}  \n  indicateurs : {ind}")

    L.append("\n## Prédictions brutes")
    for p in analyse["predictions"]:
        L.append(f"- **{p['id']}** (p={p['probability']}, échéance {p.get('horizon','?')}) — {p['question']}")

    if analyse.get("signaux_faibles"):
        L.append("\n## Signaux faibles")
        for sf in analyse["signaux_faibles"]:
            L.append(f"- {sf.get('direction','')} [{sf.get('significance','')}] {sf.get('signal','')}")

    if analyse.get("risque"):
        L.append(f"\n## Évaluation du risque\n{analyse['risque']}")
    if analyse.get("recommandations"):
        L.append("\n## Recommandations")
        for r in analyse["recommandations"]:
            L.append(f"- {r}")

    L.append("\n## Transmission → IRIS-Station")
    L.append("La formalisation (matrice ACH multi-hypothèses, Bayes logarithmique) et "
             "la calibration agrégée (Murphy, patterns sur N) relèvent d'IRIS-Station. "
             "Ce rapport fournit les hypothèses brutes et les prédictions à scorer.")
    return "\n".join(L) + "\n"


def exporter(analyse: dict, chemin_sortie: str | Path, strict: bool = False) -> str:
    """Construit, VALIDE, puis écrit rapport-osint.md. Lève si non conforme."""
    ex = construire_echange(analyse)

    rapport = xf.valider(ex)
    if not rapport.ok or (strict and rapport.avertissements):
        details = "\n".join(f"  - {c} : {m}" for c, m in rapport.erreurs)
        raise ValueError(
            "Rapport NON conforme au contrat d'échange — rien n'est écrit.\n" + details
        )

    tete = yaml.safe_dump(ex, allow_unicode=True, sort_keys=False)
    corps = _corps_markdown(analyse, ex)
    texte = f"---\n{tete}---\n\n{corps}"
    Path(chemin_sortie).write_text(texte, encoding="utf-8")
    return str(chemin_sortie)

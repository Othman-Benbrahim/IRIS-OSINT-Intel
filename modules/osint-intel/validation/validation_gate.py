#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validation_gate.py — Barrière de validation humaine (Phase 3).

Matérialise la règle : RIEN N'EST ANALYSÉ SANS VALIDATION.

- charge un corpus.md produit par la Phase 2 ;
- expose ses sources pour relecture ;
- applique la décision humaine (sources gardées + ajouts manuels) ;
- écrit un corpus-valide.md portant un bloc `validation`;
- `est_valide()` est le verrou que la Phase 4 doit interroger avant toute analyse.

Aucune logique réseau ici : pure transformation de données, testable seule.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml


# --- Lecture du corpus -----------------------------------------------------

def _extraire_front_matter(texte: str) -> str:
    texte = texte.lstrip("\ufeff")
    lignes = texte.splitlines()
    if not lignes or lignes[0].strip() != "---":
        return texte
    for i in range(1, len(lignes)):
        if lignes[i].strip() in ("---", "..."):
            return "\n".join(lignes[1:i])
    raise ValueError("Front matter ouvert par `---` mais jamais refermé.")


def charger_corpus(source) -> dict:
    """Renvoie le dict sous la clé `corpus`."""
    if isinstance(source, (str, Path)) and Path(str(source)).exists():
        texte = Path(source).read_text(encoding="utf-8")
    else:
        texte = str(source)
    doc = yaml.safe_load(_extraire_front_matter(texte)) or {}
    corpus = doc.get("corpus")
    if not isinstance(corpus, dict):
        raise ValueError("Bloc `corpus` absent ou invalide.")
    return corpus


def sources_a_valider(corpus: dict) -> list[dict]:
    """Liste relisable des sources : une entrée par assertion sourcée."""
    out = []
    for a in corpus.get("assertions", []):
        out.append({
            "url": a.get("url", ""),
            "extrait": a.get("texte", ""),
            "fiabilite": a.get("fiabilite"),
            "backend": a.get("backend", ""),
            "archive_url": a.get("archive_url"),
        })
    return out


def statistiques(corpus: dict) -> dict:
    src = sources_a_valider(corpus)
    return {
        "question": corpus.get("question", ""),
        "total": len(src),
        "fiabilite_globale": corpus.get("fiabilite_globale", 0.0),
        "backends": sorted({s["backend"] for s in src if s["backend"]}),
        "inaccessibles": len(corpus.get("inaccessibles", [])),
    }


# --- Application de la décision humaine ------------------------------------

def appliquer_validation(corpus: dict, urls_gardees, ajouts=None) -> dict:
    """Filtre le corpus aux sources retenues + ajouts manuels, et y appose le
    bloc `validation` qui ouvre la porte de la Phase 4."""
    ajouts = ajouts or []
    gardees_set = set(urls_gardees)
    assertions = corpus.get("assertions", [])

    retenues = [a for a in assertions if a.get("url") in gardees_set]
    n_rejetees = len(assertions) - len(retenues)

    for add in ajouts:
        retenues.append({
            "texte": add.get("extrait", ""),
            "url": add.get("url", ""),
            "fiabilite": add.get("fiabilite", 3),
            "backend": "manuel",
            "archive_url": None,
        })

    nouveau = dict(corpus)
    nouveau["assertions"] = retenues
    fiabs = [a["fiabilite"] for a in retenues
             if isinstance(a.get("fiabilite"), (int, float))]
    nouveau["fiabilite_globale"] = round(sum(fiabs) / len(fiabs), 2) if fiabs else 0.0
    nouveau["validation"] = {
        "valide": True,
        "par": "humain",
        "horodatage": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "gardees": len(retenues) - len(ajouts),
        "rejetees": n_rejetees,
        "ajouts_manuels": len(ajouts),
    }
    return nouveau


def est_valide(corpus: dict) -> bool:
    """VERROU. La Phase 4 doit refuser tout corpus pour lequel ceci est faux."""
    return bool((corpus.get("validation") or {}).get("valide"))


def exiger_validation(corpus: dict) -> None:
    """À appeler en tête de la Phase 4 : lève si le corpus n'est pas validé."""
    if not est_valide(corpus):
        raise PermissionError(
            "Corpus non validé : aucune analyse possible. Passez d'abord par "
            "la barrière de validation humaine (Phase 3)."
        )


# --- Écriture du corpus validé --------------------------------------------

def ecrire_corpus_valide(corpus: dict, chemin: str | Path) -> str:
    tete = yaml.safe_dump({"corpus": corpus}, allow_unicode=True, sort_keys=False)
    v = corpus["validation"]
    lignes = [
        f"# Corpus validé — {corpus.get('question', '')}",
        "",
        f"_Validé le {v['horodatage']} · {v['gardees']} gardée(s), "
        f"{v['rejetees']} rejetée(s), {v['ajouts_manuels']} ajout(s) manuel(s) · "
        f"fiabilité globale {corpus['fiabilite_globale']}/5_",
        "",
        "## Sources retenues",
    ]
    for a in corpus.get("assertions", []):
        lignes.append(f"- [{a.get('fiabilite')}/5] {a.get('texte','')} — "
                      f"{a.get('url','')}  ({a.get('backend','')})")
        if a.get("archive_url"):
            lignes.append(f"  ↳ archive : {a['archive_url']}")
    texte = f"---\n{tete}---\n\n" + "\n".join(lignes) + "\n"
    Path(chemin).write_text(texte, encoding="utf-8")
    return str(chemin)

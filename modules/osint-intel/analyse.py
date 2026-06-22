#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
analyse.py — Pipeline d'analyse TERRAIN (Phase 4).

Du corpus validé (Phase 3) à un objet d'analyse brut : hypothèses concurrentes
(priors intuitifs, ≥3), scénarios + indicateurs, prédictions brutes, signaux
faibles, biais, lacunes, recommandations.

NIVEAU TERRAIN STRICT (cf. décision terrain/labo) :
  - Bayes SIMPLE 1H×1E uniquement (`bayes_simple`).
  - Brier UNITAIRE uniquement (`brier_unitaire`).
  - Toute matrice ACH multi-hypothèses ou calibration agrégée -> « → IRIS-Station ».

L'analyse est de l'inférence : elle REQUIERT un LLM (`llm` : callable str -> str).
Pas de repli « déterministe » qui inventerait des hypothèses — ce serait une
fabrication. Le post-traitement déterministe se limite à borner et normaliser.
"""

from __future__ import annotations

import json
import re

PROB_MIN, PROB_MAX = 0.05, 0.95


# --- Outils terrain (brut) -------------------------------------------------

def borner(p: float) -> float:
    """Ramène une probabilité dans [0.05, 0.95] — jamais 0 ni 1."""
    try:
        return max(PROB_MIN, min(PROB_MAX, float(p)))
    except (TypeError, ValueError):
        return PROB_MIN


def bayes_simple(prior: float, p_e_si_h: float, p_e_si_non_h: float) -> dict:
    """Mise à jour bayésienne TERRAIN : une hypothèse, une observation.
    Renvoie posterior + facteur de Bayes. Le multi-hypothèses formel → IRIS-Station."""
    prior = borner(prior)
    num = p_e_si_h * prior
    den = num + p_e_si_non_h * (1 - prior)
    posterior = borner(num / den) if den else prior
    fb = (p_e_si_h / p_e_si_non_h) if p_e_si_non_h else float("inf")
    return {"prior": round(prior, 3), "posterior": round(posterior, 3),
            "facteur_bayes": round(fb, 3)}


def brier_unitaire(probabilite: float, issue: int) -> float:
    """Brier d'UNE prédiction (issue ∈ {0,1}). La courbe/Murphy agrégé → IRIS-Station."""
    return round((borner(probabilite) - issue) ** 2, 4)


def matrice_ach(*_a, **_k):
    raise NotImplementedError("Matrice ACH multi-hypothèses → IRIS-Station (niveau laboratoire).")


def calibration_agregee(*_a, **_k):
    raise NotImplementedError("Calibration agrégée (Murphy, patterns sur N) → IRIS-Station.")


# --- Prompt d'analyse ------------------------------------------------------

_PROMPT_ANALYSE = """\
Tu es l'analyste terrain d'OSINT-Intel. À partir UNIQUEMENT des assertions sourcées
ci-dessous, produis une analyse de PREMIER JET (niveau terrain). Tu formules des
hypothèses et des scénarios ; tu ne fais PAS de matrice ACH formelle ni de
calibration agrégée (cela relève d'IRIS-Station). Tu n'inventes aucun fait : appuie
tes hypothèses sur les assertions fournies.

Réponds UNIQUEMENT par un objet JSON valide, sans texte ni balises autour, au schéma :
{{
  "hypotheses": [{{"name": "...", "probability_prior": 0.0, "type": "dominante|dissidente|fractale"}}],
  "scenarios": [{{"name": "...", "probability": 0.0, "indicators": ["..."]}}],
  "predictions": [{{"question": "...", "probability": 0.0, "type": "binaire", "horizon": "AAAA-MM-JJ", "indicators": ["..."]}}],
  "signaux_faibles": [{{"signal": "...", "direction": "↑|↓|↗|↘|→|∅", "significance": "haute|moyenne|basse"}}],
  "biais_detectes": [{{"biais": "...", "correction": "..."}}],
  "lacunes": ["..."],
  "signaux_a_surveiller": ["..."],
  "risque": "une phrase",
  "recommandations": ["..."]
}}
Contraintes : au moins 3 hypothèses (une dominante, une dissidente, une fractale) ;
les probabilités des scénarios doivent sommer à 1 ; toute probabilité reste dans
[0.05, 0.95]. 

QUESTION : {question}

ASSERTIONS VALIDÉES (JSON) :
{assertions}
"""


def _extraire_json(texte: str) -> dict:
    t = re.sub(r"^```(?:json)?|```$", "", texte.strip(), flags=re.MULTILINE).strip()
    d, f = t.find("{"), t.rfind("}")
    if d == -1 or f == -1:
        raise ValueError("Aucun objet JSON dans la réponse du LLM.")
    return json.loads(t[d:f + 1])


# --- Pipeline --------------------------------------------------------------

def _stats_sources(assertions: list[dict]) -> dict:
    total = len(assertions)
    manuelles = sum(1 for a in assertions if a.get("backend") == "manuel")
    fiabs = [a["fiabilite"] for a in assertions
             if isinstance(a.get("fiabilite"), (int, float))]
    return {
        "total": total,
        "deep_research": total - manuelles,
        "manuelles": manuelles,
        "fiabilite_moyenne": round(sum(fiabs) / len(fiabs), 2) if fiabs else 0.0,
    }


def analyser(corpus_valide: dict, llm) -> dict:
    """corpus validé → analyse terrain brute. `llm` requis (callable str->str)."""
    if llm is None:
        raise RuntimeError(
            "L'analyse terrain requiert un LLM (branche un adaptateur Ollama/FantasyAI, "
            "ou utilise le mode --demo pour un test)."
        )

    assertions = corpus_valide.get("assertions", [])
    charge = [{"texte": a.get("texte"), "url": a.get("url"),
               "fiabilite": a.get("fiabilite"), "backend": a.get("backend")}
              for a in assertions]
    prompt = _PROMPT_ANALYSE.format(
        question=corpus_valide.get("question", ""),
        assertions=json.dumps(charge, ensure_ascii=False, indent=2),
    )
    a = _extraire_json(llm(prompt))

    # Post-traitement déterministe : identifiants, bornes, normalisation
    hyps = a.get("hypotheses", [])
    for i, h in enumerate(hyps, 1):
        h["id"] = f"H{i}"
        h["probability_prior"] = borner(h.get("probability_prior", PROB_MIN))

    scs = a.get("scenarios", [])
    somme = sum(s.get("probability", 0) for s in scs) or 1.0
    for i, s in enumerate(scs, 1):
        s["id"] = f"S{i}"
        s["probability"] = borner(round(s.get("probability", 0) / somme, 3))
        s["indicators"] = s.get("indicators", [])

    preds = a.get("predictions", [])
    for i, p in enumerate(preds, 1):
        p["id"] = f"PRED-{i:03d}"
        p["probability"] = borner(p.get("probability", PROB_MIN))
        p.setdefault("type", "binaire")
        p.setdefault("indicators", [])

    # Entités : reprises du corpus (déterministe, pas d'invention)
    entites = [{"nom": e.get("nom", ""), "type": e.get("type", "concept")}
               for e in corpus_valide.get("entites", [])[:8]]

    return {
        "question": corpus_valide.get("question", ""),
        "mode": "complet",
        "deep_research_used": corpus_valide.get("mode_collecte") != "manuel",
        "hypotheses": hyps,
        "scenarios": scs,
        "predictions": preds,
        "signaux_faibles": a.get("signaux_faibles", []),
        "entites_cles": entites,
        "biais_detectes": a.get("biais_detectes", []),
        "lacunes": a.get("lacunes", []) + corpus_valide.get("lacunes", []),
        "signaux_a_surveiller": a.get("signaux_a_surveiller", []),
        "risque": a.get("risque", ""),
        "recommandations": a.get("recommandations", []),
        "sources_stats": _stats_sources(assertions),
    }

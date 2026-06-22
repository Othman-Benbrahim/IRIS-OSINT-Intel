#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
synthesizer.py — Synthèse du corpus (étape 0.4).

Transforme les RÉSULTATS BRUTS de search.py en un CORPUS STRUCTURÉ SOURCÉ :
entités/relations, chronologie, assertions (chacune avec son URL + fiabilité 1-5),
signaux faibles, fiabilité globale.

Règles dures :
  - Synthèse uniquement — AUCUNE analyse (l'analyse commence en Phase 4).
  - AUCUNE source inventée : toute assertion renvoie à une URL réellement collectée.
  - Une affirmation non sourçable est marquée [À VÉRIFIER].

Deux voies :
  - LLM (voie principale, qualité) : on passe un `llm` (callable str -> str,
    p. ex. FantasyAI Cloud ou Ollama, cf. llm_adapters.py). Sortie JSON stricte.
  - Extractif (repli déterministe, sans LLM ni réseau) : construit le corpus
    directement à partir des résultats. Utilisé pour les tests et le hors-ligne.
    Limite assumée : ne détecte pas finement les signaux faibles (→ brancher un LLM).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

# --- Scoring de fiabilité (1-5) -------------------------------------------
# Grille externalisée dans scoring.json (éditable sans toucher au code).
# Repli sur ces valeurs par défaut si le fichier est absent ou illisible.

_SCORING_DEFAUT = {
    "defaut_web": 2,
    "backends": {"wikipedia": 3, "gdelt": 3, "news": 3},
    "paliers": [
        (5, ("imf.org", "worldbank.org", "oecd.org", "bis.org", "ecb.europa.eu",
             ".gouv.fr", ".gov", "europa.eu", "un.org", "who.int")),
        (4, ("reuters.com", "apnews.com", "afp.com", "bloomberg.com", "ft.com",
             "wsj.com", "lemonde.fr", "economist.com", "nature.com", "science.org",
             ".edu", "arxiv.org")),
        (3, ("wikipedia.org", "britannica.com")),
        (1, ("medium.com", "substack.com", "reddit.com", "x.com", "twitter.com",
             "facebook.com", "wordpress.com", "blogspot.com", "quora.com")),
    ],
    "corroboration": {"actif": True, "bonus": 1, "seuil_similarite": 0.3},
}

_SCORING_CACHE = None


def _scoring() -> dict:
    """Charge scoring.json une fois ; repli sur les valeurs par défaut."""
    global _SCORING_CACHE
    if _SCORING_CACHE is not None:
        return _SCORING_CACHE
    f = Path(__file__).with_name("scoring.json")
    try:
        cfg = json.loads(f.read_text(encoding="utf-8"))
        paliers = [(p["note"], tuple(p["domaines"])) for p in cfg.get("paliers", [])]
        _SCORING_CACHE = {
            "defaut_web": cfg.get("defaut_web", 2),
            "backends": cfg.get("backends", {}),
            "paliers": paliers or _SCORING_DEFAUT["paliers"],
            "corroboration": cfg.get("corroboration", _SCORING_DEFAUT["corroboration"]),
        }
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        _SCORING_CACHE = _SCORING_DEFAUT
    return _SCORING_CACHE


def fiabilite_source(backend: str, url: str) -> int:
    """Note 1-5. La grille DOMAINE fait autorité ; le type de backend n'est
    qu'un repli quand le domaine n'est pas reconnu."""
    cfg = _scoring()
    u = (url or "").lower()
    for note, domaines in cfg["paliers"]:
        if any(d in u for d in domaines):
            return note
    base = cfg["backends"].get(backend)
    if base is not None:
        return base
    return cfg["defaut_web"]


def _domaine(url: str) -> str:
    m = re.search(r"https?://([^/]+)", (url or "").lower())
    h = (m.group(1) if m else "").split(":")[0]
    return h[4:] if h.startswith("www.") else h


def _tokens(texte: str) -> set:
    return {t for t in re.findall(r"[a-zà-ÿ0-9]{4,}", (texte or "").lower())}


def appliquer_corroboration(assertions: list) -> None:
    """+bonus (plafonné à 5) à toute assertion confirmée par au moins une source
    d'un DOMAINE différent (similarité de tokens >= seuil). Marque `corrobore`.
    Les sources non sourcées ([À VÉRIFIER]) n'en bénéficient jamais."""
    for a in assertions:
        a.setdefault("corrobore", False)
    cfg = _scoring().get("corroboration", {})
    if not cfg.get("actif", True) or len(assertions) < 2:
        return
    bonus = cfg.get("bonus", 1)
    seuil = cfg.get("seuil_similarite", 0.3)
    valide = [str(a.get("url", "")).startswith("http") for a in assertions]
    toks = [_tokens(a.get("texte", "")) for a in assertions]
    doms = [_domaine(a.get("url", "")) for a in assertions]
    for i, a in enumerate(assertions):
        if not valide[i] or not toks[i]:
            continue
        for j in range(len(assertions)):
            if i == j or not valide[j] or doms[i] == doms[j] or not toks[j]:
                continue
            if len(toks[i] & toks[j]) / len(toks[i] | toks[j]) >= seuil:
                a["corrobore"] = True
                break
        if a["corrobore"]:
            a["fiabilite"] = min(5, (a.get("fiabilite") or 0) + bonus)


# --- Voie extractive (déterministe) ---------------------------------------

def _phrases(texte: str) -> list[str]:
    bouts = re.split(r"(?<=[.!?])\s+", (texte or "").strip())
    return [b.strip() for b in bouts if len(b.strip()) > 20]


def _synthese_extractive(collecte: dict) -> dict:
    resultats = collecte["resultats"]
    parse = collecte["parse"]

    # Entités : entités du parse + comptage des termes capitalisés dans les titres
    compteur = Counter()
    for ent in parse.get("entites", []):
        compteur[ent] += 2
    for r in resultats:
        for m in re.findall(r"[A-ZÀ-Ý][\wÀ-ÿ'’-]{2,}(?:\s+[A-ZÀ-Ý][\wÀ-ÿ'’-]+)*",
                            r.get("titre", "")):
            compteur[m] += 1
    entites = [{"nom": n, "type": "à_qualifier", "occurrences": c}
               for n, c in compteur.most_common(10)]

    # Assertions : 1re phrase exploitable de chaque résultat, sourcée + notée
    assertions = []
    for r in resultats:
        fia = fiabilite_source(r["backend"], r.get("url", ""))
        bouts = _phrases(r.get("extrait", "")) or ([r.get("titre", "").strip()]
                                                   if r.get("titre") else [])
        if not bouts:
            continue
        assertions.append({
            "texte": bouts[0],
            "url": r.get("url", "") or "[À VÉRIFIER]",
            "fiabilite": fia,
            "backend": r["backend"],
            "archive_url": r.get("archive_url"),
            "date": r.get("date"),
        })

    # Chronologie : résultats datés
    chronologie = [
        {"date": r["date"], "evenement": r.get("titre", ""), "url": r.get("url", "")}
        for r in resultats if r.get("date")
    ]
    chronologie.sort(key=lambda x: str(x["date"]))

    appliquer_corroboration(assertions)  # +bonus si confirmé par un autre domaine
    fiabs = [a["fiabilite"] for a in assertions]
    fiab_globale = round(sum(fiabs) / len(fiabs), 2) if fiabs else 0.0

    lacunes = []
    if collecte.get("inaccessibles"):
        lacunes.append(f"{len(collecte['inaccessibles'])} source(s) inaccessible(s) "
                       "lors de la collecte")
    lacunes.append("Signaux faibles non détectés en mode extractif — brancher un LLM "
                   "(synthetiser(..., llm=...)) pour cette étape.")

    return {
        "mode_synthese": "extractif",
        "entites": entites,
        "relations": [],
        "chronologie": chronologie,
        "assertions": assertions,
        "signaux_faibles": [],
        "fiabilite_globale": fiab_globale,
        "lacunes": lacunes,
    }


# --- Voie LLM --------------------------------------------------------------

_PROMPT_SYNTHESE = """\
Tu es le synthétiseur d'OSINT-Intel. Ta SEULE tâche est de SYNTHÉTISER les
résultats bruts ci-dessous. Tu n'analyses pas, tu ne conclus pas, tu n'évalues
aucune hypothèse. Tu n'inventes JAMAIS de source : chaque assertion doit
renvoyer à une URL présente dans les résultats. Une affirmation que tu ne peux
rattacher à aucune URL fournie doit être marquée "[À VÉRIFIER]" dans son champ url.

Réponds UNIQUEMENT par un objet JSON valide, sans texte autour, sans balises de
code, au schéma EXACT suivant :
{{
  "entites": [{{"nom": "...", "type": "institution|pays|concept|personne|entreprise", "occurrences": 0}}],
  "relations": [{{"de": "...", "vers": "...", "type": "..."}}],
  "chronologie": [{{"date": "AAAA-MM-JJ", "evenement": "...", "url": "..."}}],
  "assertions": [{{"texte": "...", "url": "...", "fiabilite": 1, "backend": "..."}}],
  "signaux_faibles": [{{"signal": "...", "url": "...", "note": "..."}}],
  "fiabilite_globale": 0.0,
  "lacunes": ["..."]
}}
"fiabilite" est un entier 1-5. N'utilise que les URLs présentes ci-dessous.

QUESTION : {question}

RÉSULTATS BRUTS (JSON) :
{resultats}
"""


def _extraire_json(texte: str) -> dict:
    t = texte.strip()
    t = re.sub(r"^```(?:json)?|```$", "", t, flags=re.MULTILINE).strip()
    debut, fin = t.find("{"), t.rfind("}")
    if debut == -1 or fin == -1:
        raise ValueError("Aucun objet JSON trouvé dans la réponse du LLM.")
    return json.loads(t[debut:fin + 1])


def _synthese_llm(collecte: dict, llm) -> dict:
    charge = [
        {"titre": r.get("titre"), "url": r.get("url"), "extrait": r.get("extrait"),
         "backend": r.get("backend"), "date": r.get("date")}
        for r in collecte["resultats"]
    ]
    prompt = _PROMPT_SYNTHESE.format(
        question=collecte["question"],
        resultats=json.dumps(charge, ensure_ascii=False, indent=2),
    )
    brut = llm(prompt)
    corpus = _extraire_json(brut)
    corpus["mode_synthese"] = "llm"
    corpus.setdefault("relations", [])
    corpus.setdefault("signaux_faibles", [])
    corpus.setdefault("lacunes", [])

    # Garde-fou : aucune URL inventée. On neutralise les assertions dont l'URL
    # n'est pas dans les résultats collectés (sauf marquage [À VÉRIFIER]).
    # (3) La grille domaine déterministe fait autorité — pas la note du LLM.
    urls_valides = {r.get("url") for r in collecte["resultats"]}
    for a in corpus.get("assertions", []):
        if a.get("url") not in urls_valides and a.get("url") != "[À VÉRIFIER]":
            a["url"] = "[À VÉRIFIER]"
            a["fiabilite"] = 1
        elif a.get("url") == "[À VÉRIFIER]":
            a["fiabilite"] = 1
        else:
            a["fiabilite"] = fiabilite_source(a.get("backend", ""), a.get("url", ""))
    appliquer_corroboration(corpus["assertions"])
    fiabs = [a["fiabilite"] for a in corpus["assertions"]]
    corpus["fiabilite_globale"] = round(sum(fiabs) / len(fiabs), 2) if fiabs else 0.0
    return corpus


# --- Point d'entrée --------------------------------------------------------

def synthetiser(collecte: dict, llm=None) -> dict:
    """Synthétise les résultats bruts en corpus structuré.

    `llm` : callable str -> str. Si None, repli extractif déterministe.
    En cas d'échec du LLM (réponse non JSON, exception), repli extractif
    avec mention dans `lacunes`.
    """
    if llm is None:
        return _synthese_extractive(collecte)
    try:
        return _synthese_llm(collecte, llm)
    except Exception as exc:
        corpus = _synthese_extractive(collecte)
        corpus["lacunes"].insert(0, f"Synthèse LLM échouée ({type(exc).__name__}) "
                                    "— repli extractif appliqué.")
        return corpus


# --- Sérialisation corpus.md ----------------------------------------------

def corpus_vers_md(collecte: dict, corpus: dict) -> str:
    """Produit un corpus.md : front matter machine + corps lisible (humain)."""
    import yaml  # dépendance déjà requise par le projet

    fm = {
        "corpus": {
            "version": "1.0",
            "question": collecte["question"],
            "horodatage": collecte["horodatage"],
            "mode_collecte": collecte["mode_collecte"],
            "mode_synthese": corpus["mode_synthese"],
            "hors_ligne": collecte["hors_ligne"],
            "backends_actifs": collecte["backends_actifs"],
            "parse": collecte["parse"],
            "requetes": collecte["requetes"],
            "entites": corpus["entites"],
            "relations": corpus["relations"],
            "chronologie": corpus["chronologie"],
            "assertions": corpus["assertions"],
            "signaux_faibles": corpus["signaux_faibles"],
            "fiabilite_globale": corpus["fiabilite_globale"],
            "lacunes": corpus["lacunes"],
            "inaccessibles": collecte["inaccessibles"],
        }
    }
    tete = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False)

    lignes = [f"# Corpus Deep Research — {collecte['question']}", ""]
    lignes.append(f"_Collecte {collecte['mode_collecte']} · synthèse "
                  f"{corpus['mode_synthese']} · fiabilité globale "
                  f"{corpus['fiabilite_globale']}/5 · "
                  f"{len(corpus['assertions'])} assertion(s)_")
    lignes.append("")
    lignes.append("## Assertions sourcées")
    for a in corpus["assertions"]:
        marque = " ✓corroboré" if a.get("corrobore") else ""
        dt = f" · {str(a['date'])[:10]}" if a.get("date") else ""
        lignes.append(f"- [{a['fiabilite']}/5{marque}] {a['texte']} — {a['url']}  "
                      f"({a['backend']}{dt})")
        if a.get("archive_url"):
            lignes.append(f"  ↳ archive : {a['archive_url']}")
    if corpus["chronologie"]:
        lignes.append("\n## Chronologie")
        for c in corpus["chronologie"]:
            lignes.append(f"- {c['date']} — {c['evenement']} ({c['url']})")
    if corpus["signaux_faibles"]:
        lignes.append("\n## Signaux faibles")
        for s in corpus["signaux_faibles"]:
            lignes.append(f"- {s.get('signal','')} — {s.get('url','')}")
    if corpus["lacunes"]:
        lignes.append("\n## Lacunes")
        for l in corpus["lacunes"]:
            lignes.append(f"- {l}")
    if collecte["inaccessibles"]:
        lignes.append("\n## Sources inaccessibles")
        for i in collecte["inaccessibles"]:
            lignes.append(f"- {i['backend']} / {i['requete']} : {i['raison']}")

    return f"---\n{tete}---\n\n" + "\n".join(lignes) + "\n"

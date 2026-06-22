#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
search.py — Moteur de collecte Deep Research (étape 0.1 → 0.3).

Responsabilité STRICTE : transformer une question en RÉSULTATS BRUTS sourcés.
  0.1  parse de la question   (entités, domaine, horizon, termes-clés)
  0.2  génération de 3-5 requêtes multi-angles
  0.3  interrogation des backends

Backends « généralistes » interchangeables, essayés en CHAÎNE DE REPLI par ordre
de `priorite` (le plus petit d'abord) : SearXNG, DuckDuckGo, News. Le premier qui
renvoie des résultats pour une requête l'emporte ; s'il échoue ou ne renvoie rien,
on passe au suivant. Backends « spécialisés » (Wikipedia, ArXiv) : additifs,
conditionnels, sans repli.

Aucune source inventée : une source injoignable est marquée [inaccessible].
Dépendances web importées de façon paresseuse : le module se charge sans `ddgs`.
SearXNG et Wikipedia/ArXiv n'utilisent que la bibliothèque standard.
"""

from __future__ import annotations

import json
import os
import re
import socket
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

# --- Listes outils ---------------------------------------------------------

_ELISIONS = {"d", "l", "qu", "n", "s", "j", "t", "m", "c"}

_STOPWORDS = {
    "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou", "à", "au",
    "aux", "en", "dans", "sur", "pour", "par", "est", "sera", "quelle", "quel",
    "quels", "quelles", "ce", "cette", "ces", "il", "elle", "y", "a", "que",
    "the", "of", "in", "on", "for", "and", "or", "is", "will", "be", "what",
    "probabilité", "probabilite", "impact",
}

_MOTS_ACADEMIQUES = {
    "étude", "etude", "recherche", "modèle", "modele", "modèles", "modeles",
    "algorithme", "théorème", "theoreme", "quantique", "protéine", "proteine",
    "neural", "neuronal", "paper", "preprint", "arxiv", "hypothèse", "hypothese",
    "équation", "cybersécurité", "cybersecurite",
}


# --- 0.1  Parse de la question --------------------------------------------

def _tokeniser(texte: str) -> list[str]:
    # On remplace les apostrophes par des espaces pour casser les élisions
    norm = re.sub(r"[''’]", " ", texte.lower())
    return re.findall(r"[\wÀ-ÿ-]+", norm)


def parser_question(question: str, maintenant: datetime | None = None) -> dict:
    maintenant = maintenant or datetime.now(timezone.utc)
    q = question.strip()

    entites = re.findall(r"[A-ZÀ-Ý][\wÀ-ÿ'’-]+(?:\s+[A-ZÀ-Ý][\wÀ-ÿ'’-]+)*", q)
    # On retire les interrogatifs initiaux fréquents
    entites = [e for e in dict.fromkeys(entites)
               if len(e) > 2 and e.lower() not in {"quelle", "quel", "quels",
                                                    "quelles", "comment", "pourquoi"}]

    mots = [m for m in _tokeniser(q) if m not in _ELISIONS]
    termes = [m for m in dict.fromkeys(mots) if m not in _STOPWORDS and len(m) > 2]

    annees = [int(a) for a in re.findall(r"\b(20\d{2})\b", q)]
    horizon_mois = None
    if annees:
        cible = max(annees)
        horizon_mois = max(0, (cible - maintenant.year) * 12 + (12 - maintenant.month))

    academique = any(m in _MOTS_ACADEMIQUES for m in termes)

    return {
        "question": q,
        "entites": entites[:8],
        "termes_cles": termes[:12],
        "horizon_mois": horizon_mois,
        "domaine_academique": academique,
    }


# --- 0.2  Génération de requêtes ------------------------------------------

def generer_requetes(parse: dict) -> list[dict]:
    base_termes = parse["termes_cles"][:5] or parse["entites"][:3]
    sujet = " ".join(base_termes).strip() or parse["question"]
    annee_proche = datetime.now(timezone.utc).year + 1

    requetes = [
        {"angle": "factuel", "requete": sujet},
        {"angle": "prospectif", "requete": f"{sujet} perspectives {annee_proche}"},
        {"angle": "contradictoire", "requete": f"{sujet} risques critiques arguments contre"},
        {"angle": "signaux_faibles", "requete": f"{sujet} signes avant-coureurs signaux faibles"},
        {"angle": "contexte", "requete": f"{sujet}"},
    ]
    vues, propres = set(), []
    for r in requetes:
        if r["requete"] not in vues:
            vues.add(r["requete"])
            propres.append(r)
    return propres[:5]


# --- Backends --------------------------------------------------------------

class Backend:
    id = "base"
    type = "base"
    role = "generaliste"          # "generaliste" (chaîne de repli) | "specialise" (additif)
    local = False
    angles: set[str] = set()

    def condition_remplie(self, parse: dict, cfg: dict) -> bool:
        cond = cfg.get("condition", "toujours")
        if cond in ("toujours", "contexte"):
            return True
        if cond == "domaine_academique":
            return bool(parse.get("domaine_academique"))
        if cond == "horizon_court":
            h = parse.get("horizon_mois")
            return h is not None and h <= cfg.get("horizon_max_mois", 12)
        return True

    def rechercher(self, requete: str, max_resultats: int, angle: str | None = None,
                   recence: str | None = None) -> list[dict]:
        raise NotImplementedError


# Fraîcheur → filtres natifs des API
_DDG_TIMELIMIT = {"jour": "d", "semaine": "w", "mois": "m", "annee": "y"}
_SEARXNG_RANGE = {"jour": "day", "semaine": "week", "mois": "month", "annee": "year"}
_TAVILY_RANGE = {"jour": "day", "semaine": "week", "mois": "month", "annee": "year"}
# GDELT : fenêtre glissante de 3 mois maximum. On élargit volontairement (mois/année
# -> 3m) : le tri datedesc fait déjà remonter le plus récent ; une fenêtre serrée ne
# ferait que réduire le rappel et renvoyer du vide. "jour"/"semaine" restent serrés
# pour qui veut explicitement du très frais.
_GDELT_TIMESPAN = {"jour": "1d", "semaine": "1w", "mois": "3m", "annee": "3m"}
# GDELT impose ~1 requête / 5 s (sinon HTTP 429). Throttle inter-appels.
_GDELT_INTERVALLE = 5.0
_gdelt_dernier_appel = 0.0
_UA_NAVIGATEUR = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")


def _date_gdelt(s: str) -> str | None:
    """seendate GDELT '20260619T143000Z' -> '2026-06-19'."""
    s = (s or "").strip()
    if len(s) >= 8 and s[:8].isdigit():
        return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
    return s or None


# Mots de décoration ajoutés par generer_requetes : inutiles (et nuisibles) pour
# GDELT, qui combine tous les termes par ET.
_GDELT_DECOR = {"perspectives", "perspective", "risques", "critiques", "arguments",
                "contre", "signes", "avant-coureurs", "avant", "coureurs", "signaux",
                "faibles", "tendances"}


def _requete_gdelt(requete: str, n: int = 3) -> str:
    """Réduit une requête multi-angles aux ~3 mots-clés cœur (ET chez GDELT).
    Retire stopwords, décoration et années nues, qui rendraient le ET stérile.
    Découpe sur les tirets : GDELT rejette les mots-clés contenant un '-'."""
    cle: list[str] = []
    for m in re.findall(r"[\wÀ-ÿ]+", requete.lower()):   # pas de tiret -> pas de '-'
        if (m in _STOPWORDS or m in _GDELT_DECOR or len(m) <= 2
                or re.fullmatch(r"20\d{2}", m)):
            continue
        if m not in cle:
            cle.append(m)
    return " ".join(cle[:n]) if cle else requete


class SearxngBackend(Backend):
    """Métamoteur auto-hébergé. Voie privilégiée (priorité basse dans sources.json).
    Requiert que le format JSON soit activé dans settings.yml (search.formats),
    sinon l'instance renvoie 403."""

    id = "searxng"
    type = "web"
    role = "generaliste"
    angles = {"factuel", "contradictoire", "signaux_faibles", "prospectif"}

    def __init__(self, instance="http://localhost:8080", lang="fr"):
        self.instance = instance.rstrip("/")
        self.lang = lang

    def rechercher(self, requete, max_resultats, angle=None, recence=None):
        import urllib.error
        import urllib.parse
        import urllib.request
        categorie = "news" if angle == "prospectif" else "general"
        p = {"q": requete, "format": "json", "language": self.lang, "categories": categorie}
        if categorie == "news" and recence in _SEARXNG_RANGE:  # fraîcheur : news seulement
            p["time_range"] = _SEARXNG_RANGE[recence]
        params = urllib.parse.urlencode(p)
        url = f"{self.instance}/search?{params}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "OSINT-Intel/1.0 (+deep-research)",
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as rep:
                data = json.loads(rep.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                raise RuntimeError(
                    "SearXNG 403 : format JSON non activé (ajoutez 'json' à "
                    "search.formats dans settings.yml)"
                ) from exc
            raise
        out = []
        for r in data.get("results", [])[:max_resultats]:
            out.append({
                "titre": r.get("title", ""),
                "url": r.get("url", ""),
                "extrait": r.get("content", ""),
                "date": r.get("publishedDate"),
            })
        return out


class DuckDuckGoBackend(Backend):
    id = "duckduckgo"
    type = "web"
    role = "generaliste"
    angles = {"factuel", "contradictoire", "signaux_faibles"}

    def rechercher(self, requete, max_resultats, angle=None, recence=None):
        from ddgs import DDGS
        # Web généraliste : pas de filtre temporel (la fraîcheur ne vise que les news).
        bruts = DDGS().text(requete, max_results=max_resultats)
        return [{"titre": b.get("title", ""),
                 "url": b.get("href") or b.get("url", ""),
                 "extrait": b.get("body", ""), "date": None} for b in bruts]


class NewsBackend(Backend):
    id = "news"
    type = "actualite"
    role = "generaliste"
    angles = {"prospectif"}

    def rechercher(self, requete, max_resultats, angle=None, recence=None):
        from ddgs import DDGS
        bruts = DDGS().news(requete, max_results=max_resultats,
                            timelimit=_DDG_TIMELIMIT.get(recence))
        return [{"titre": b.get("title", ""),
                 "url": b.get("url") or b.get("href", ""),
                 "extrait": b.get("body", ""), "date": b.get("date")} for b in bruts]


class GdeltBackend(Backend):
    """Actualité datée mondiale — API GDELT DOC 2.0 (gratuite, sans clé, sans install).

    Fenêtre glissante de 3 mois. Renvoie titre + URL + date (seendate), trié du plus
    récent au plus ancien. GDELT combine les termes par ET : des requêtes courtes
    fonctionnent mieux que de longues phrases."""

    id = "gdelt"
    type = "actualite"
    role = "generaliste"
    angles = {"prospectif", "signaux_faibles"}

    def __init__(self):
        self._cache: dict = {}  # mémoïse par requête nettoyée (évite les doublons)

    def rechercher(self, requete, max_resultats, angle=None, recence=None):
        import urllib.error
        import urllib.parse
        import urllib.request
        global _gdelt_dernier_appel
        n = min(max(int(max_resultats), 1), 250)
        q = _requete_gdelt(requete)
        timespan = _GDELT_TIMESPAN.get(recence, "3m")
        cle = (q, timespan, n)
        if cle in self._cache:                 # déjà interrogé dans cette collecte
            return self._cache[cle]
        params = urllib.parse.urlencode({
            "query": q,
            "mode": "artlist",
            "format": "json",
            "maxrecords": n,
            "timespan": timespan,
            "sort": "datedesc",
        })
        url = f"https://api.gdeltproject.org/api/v2/doc/doc?{params}"
        req = urllib.request.Request(url, headers={
            "User-Agent": _UA_NAVIGATEUR, "Accept": "application/json"})

        # Jusqu'à 2 tentatives : sur 429 (limite côté serveur), on attend le délai
        # imposé puis on réessaie une fois. Le throttle en tête de boucle gère l'attente.
        brut = ""
        for tentative in range(2):
            attente = _GDELT_INTERVALLE - (time.monotonic() - _gdelt_dernier_appel)
            if attente > 0:
                time.sleep(attente)
            _gdelt_dernier_appel = time.monotonic()
            try:
                with urllib.request.urlopen(req, timeout=15) as rep:
                    brut = rep.read().decode("utf-8", "ignore").strip()
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 429 and tentative == 0:
                    continue  # le throttle attendra ~5 s avant de réessayer
                detail = ""
                try:
                    detail = exc.read().decode("utf-8", "ignore")[:200]
                except Exception:
                    pass
                self._cache[cle] = []  # échec mémorisé : pas de rappel pour cette collecte
                raise RuntimeError(
                    f"GDELT HTTP {exc.code} : {detail or exc.reason}") from exc
        if not brut:
            self._cache[cle] = []
            return []
        try:
            data = json.loads(brut)
        except json.JSONDecodeError as exc:
            # GDELT renvoie ses refus en texte (requête trop courte/longue, etc.)
            self._cache[cle] = []  # échec mémorisé : pas de rappel pour cette collecte
            raise RuntimeError(f"GDELT a refusé la requête : {brut[:200]}") from exc
        out = []
        for a in data.get("articles", [])[:n]:
            out.append({
                "titre": a.get("title", ""),
                "url": a.get("url", ""),
                "extrait": a.get("title", ""),  # ArtList ne fournit pas de corps
                "date": _date_gdelt(a.get("seendate", "")),
            })
        self._cache[cle] = out
        return out


class WikipediaBackend(Backend):
    id = "wikipedia"
    type = "encyclopedie"
    role = "specialise"
    angles = {"contexte"}

    def __init__(self, lang="fr"):
        self.lang = lang

    def rechercher(self, requete, max_resultats, angle=None, recence=None):
        import urllib.parse
        import urllib.request
        url = (f"https://{self.lang}.wikipedia.org/w/api.php?action=opensearch"
               f"&search={urllib.parse.quote(requete)}&limit={max_resultats}&format=json")
        with urllib.request.urlopen(url, timeout=8) as rep:
            data = json.loads(rep.read().decode("utf-8"))
        titres, descs, urls = data[1], data[2], data[3]
        return [{"titre": t, "url": u, "extrait": d, "date": None}
                for t, d, u in zip(titres, descs, urls)]


class ArxivBackend(Backend):
    id = "arxiv"
    type = "academique"
    role = "specialise"
    angles = {"factuel"}

    def rechercher(self, requete, max_resultats, angle=None, recence=None):
        import urllib.parse
        import urllib.request
        import xml.etree.ElementTree as ET
        url = ("http://export.arxiv.org/api/query?search_query=all:"
               f"{urllib.parse.quote(requete)}&max_results={max_resultats}"
               "&sortBy=submittedDate&sortOrder=descending")
        with urllib.request.urlopen(url, timeout=10) as rep:
            racine = ET.fromstring(rep.read())
        ns = {"a": "http://www.w3.org/2005/Atom"}
        out = []
        for e in racine.findall("a:entry", ns):
            out.append({
                "titre": (e.findtext("a:title", "", ns) or "").strip(),
                "url": (e.findtext("a:id", "", ns) or "").strip(),
                "extrait": (e.findtext("a:summary", "", ns) or "").strip(),
                "date": e.findtext("a:published", None, ns),
            })
        return out


class TavilyBackend(Backend):
    """Recherche web + actualité datée via l'API Tavily, conçue pour l'IA/RAG.

    Renvoie du contenu propre (et non de simples liens), idéal pour la synthèse.
    1000 crédits/mois gratuits, sans carte. Fonctionne aussi SANS clé (bridé) :
    si aucune clé n'est fournie, le client tourne en mode sans clé pour démarrer.
    """

    id = "tavily"
    type = "web"
    role = "generaliste"
    angles = {"factuel", "contradictoire", "signaux_faibles", "prospectif"}

    def __init__(self, cle=""):
        self.cle = (cle or "").strip()

    def rechercher(self, requete, max_resultats, angle=None, recence=None):
        from tavily import TavilyClient
        client = TavilyClient(api_key=self.cle or None)  # None -> mode sans clé
        topic = "news" if angle == "prospectif" else "general"
        n = min(max(int(max_resultats), 1), 20)
        kwargs = {"query": requete, "search_depth": "basic",
                  "topic": topic, "max_results": n}
        tr = _TAVILY_RANGE.get(recence)
        if topic == "news" and tr:                 # fraîcheur : news seulement
            kwargs["time_range"] = tr
        try:
            rep = client.search(**kwargs)
        except Exception as exc:
            raise RuntimeError(f"Tavily : {exc}"[:200]) from exc
        out = []
        for r in (rep.get("results") or [])[:n]:
            out.append({
                "titre": r.get("title", ""),
                "url": r.get("url", ""),
                "extrait": r.get("content", ""),
                "date": r.get("published_date"),   # présent pour topic=news
            })
        return out


def _date_rfc_iso(s):
    """'Tue, 23 Jun 2026 07:00:00 GMT' -> '2026-06-23' (format uniforme du projet)."""
    if not s:
        return None
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(s).strftime("%Y-%m-%d")
    except Exception:
        return None


class QwantBackend(Backend):
    """Web généraliste via l'API frontend (non officielle) de Qwant.

    Sans clé, résultats datés, index large. ATTENTION : API non documentée
    protégée par anti-bot (Cloudflare) — peut casser ou être bloquée sans
    préavis ; en cas d'échec, la chaîne de repli passe au moteur suivant.
    """

    id = "qwant"
    type = "web"
    role = "generaliste"
    angles = {"factuel", "contradictoire", "signaux_faibles", "prospectif"}

    def rechercher(self, requete, max_resultats, angle=None, recence=None):
        import urllib.parse
        import urllib.request
        n = min(max(int(max_resultats), 1), 10)
        params = urllib.parse.urlencode({"q": requete, "count": n, "locale": "fr_FR",
                                         "t": "web", "device": "desktop", "safesearch": 1})
        req = urllib.request.Request(
            "https://api.qwant.com/v3/search/web?" + params,
            headers={"User-Agent": _UA_NAVIGATEUR,
                     "Accept": "application/json, text/plain, */*",
                     "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
                     "Referer": "https://www.qwant.com/",
                     "Origin": "https://www.qwant.com",
                     "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors",
                     "Sec-Fetch-Site": "same-site"})
        with urllib.request.urlopen(req, timeout=12) as rep:
            data = json.loads(rep.read().decode("utf-8", "replace"))
        items = ((data.get("data") or {}).get("result") or {}).get("items") or []
        if isinstance(items, dict):              # certaines versions groupent
            items = items.get("mainline") or []
        out = []
        for it in items:
            if not isinstance(it, dict) or not it.get("url"):
                continue
            d = it.get("date")
            try:
                date = datetime.fromtimestamp(int(d), tz=timezone.utc).strftime("%Y-%m-%d") if d else None
            except Exception:
                date = None
            out.append({"titre": it.get("title", ""), "url": it.get("url", ""),
                        "extrait": it.get("desc", ""), "date": date})
        return out[:n]


class GNewsBackend(Backend):
    """Actualité datée via Google News (librairie gnews). Source ADDITIVE :
    elle complète Tavily sur l'angle prospectif au lieu de servir de simple repli.

    NB : les URLs renvoyées sont des redirections Google News (cliquables, mais
    pas l'URL directe de l'éditeur) ; le nom de l'éditeur est conservé.
    """

    id = "gnews"
    type = "actualite"
    role = "additif"
    angles = {"prospectif"}
    _PERIODE = {"jour": "1d", "semaine": "7d", "mois": "1m", "annee": "1y"}

    def __init__(self, lang="fr", pays="FR"):
        self.lang = lang
        self.pays = pays

    def rechercher(self, requete, max_resultats, angle=None, recence=None):
        from gnews import GNews
        n = min(max(int(max_resultats), 1), 10)
        g = GNews(language=self.lang, country=self.pays, max_results=n)
        per = self._PERIODE.get(recence)
        if per:
            g.period = per                       # filtre de fraîcheur
        out = []
        for a in (g.get_news(requete) or []):
            editeur = (a.get("publisher") or {}).get("title", "") if isinstance(a.get("publisher"), dict) else ""
            out.append({"titre": a.get("title", ""), "url": a.get("url", ""),
                        "extrait": a.get("description", "") or editeur,
                        "date": _date_rfc_iso(a.get("published date")),
                        "editeur": editeur})
        return out


class ExaBackend(Backend):
    """Recherche sémantique (neuronale) via l'API Exa — vraie API à clé.

    Source ADDITIVE : complète Tavily sur les angles d'analyse/découverte
    (factuel, contradictoire, signaux faibles), là où chercher par le sens fait
    remonter des sources non évidentes que le mot-clé rate. On ne lui confie PAS
    l'actualité (angle prospectif) : son index est plus étroit sur le très récent
    et le non-anglophone — ça reste le terrain de Tavily.

    Exa NE fonctionne PAS sans clé : sans clé renseignée, le backend est ignoré
    (la chaîne continue), il n'y a simplement pas de résultats Exa.
    """

    id = "exa"
    type = "web"
    role = "additif"
    angles = {"factuel", "contradictoire", "signaux_faibles"}

    def __init__(self, cle=""):
        self.cle = (cle or "").strip()

    def rechercher(self, requete, max_resultats, angle=None, recence=None):
        from exa_py import Exa
        if not self.cle:
            raise RuntimeError("Exa : clé API requise (panneau Configuration)")
        client = Exa(self.cle)
        n = min(max(int(max_resultats), 1), 10)
        try:
            rep = client.search(requete, num_results=n, type="auto",
                                 contents={"text": {"maxCharacters": 800}},
                                 user_location="fr")
        except Exception as exc:
            raise RuntimeError(f"Exa : {exc}"[:200]) from exc
        out = []
        for r in (getattr(rep, "results", None) or []):
            d = getattr(r, "published_date", None)
            date = d[:10] if isinstance(d, str) and len(d) >= 10 else None
            out.append({"titre": getattr(r, "title", "") or "",
                        "url": getattr(r, "url", "") or "",
                        "extrait": (getattr(r, "text", "") or "")[:600],
                        "date": date})
        return out


class WaybackBackend(Backend):
    """Enrichisseur d'archives (Internet Archive / Wayback Machine).

    N'interroge PAS par mot-clé : Wayback est indexé par URL. Pour chaque source
    déjà collectée, il récupère le snapshot archivé le plus proche — utile pour
    récupérer un lien mort ou tracer une page supprimée/modifiée. Il s'exécute en
    PASSE D'ENRICHISSEMENT après la collecte, pas dans la boucle de requêtes.
    """

    id = "wayback"
    type = "archive"
    role = "enrichissement"
    angles: set[str] = set()

    def snapshot(self, url: str):
        """Renvoie (url_archive, timestamp) ou (None, None)."""
        import urllib.parse
        import urllib.request
        api = "https://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe="")
        with urllib.request.urlopen(api, timeout=6) as rep:
            data = json.loads(rep.read().decode("utf-8"))
        proche = (data.get("archived_snapshots") or {}).get("closest") or {}
        if proche.get("available") and proche.get("url"):
            return proche["url"], proche.get("timestamp")
        return None, None

    def enrichir(self, resultats: list[dict]) -> None:
        for res in resultats:
            u = res.get("url", "")
            if not u or u.startswith("[") or "archive_url" in res:
                continue
            try:
                arch, ts = self.snapshot(u)
            except Exception:
                arch, ts = None, None
            res["archive_url"] = arch
            res["archive_timestamp"] = ts


_BACKENDS_WEB = {
    "tavily": TavilyBackend,
    "exa": ExaBackend,
    "qwant": QwantBackend,
    "gnews": GNewsBackend,
    "gdelt": GdeltBackend,
    "searxng": SearxngBackend,
    "duckduckgo": DuckDuckGoBackend,
    "news": NewsBackend,
    "wikipedia": WikipediaBackend,
    "arxiv": ArxivBackend,
    "wayback": WaybackBackend,
}


def _instancier(sid: str, cfg: dict) -> Backend | None:
    if sid == "tavily":
        return TavilyBackend(cle=cfg.get("cle", ""))
    if sid == "exa":
        return ExaBackend(cle=cfg.get("cle", ""))
    if sid == "gnews":
        return GNewsBackend(lang=cfg.get("lang", "fr"), pays=cfg.get("pays", "FR"))
    if sid == "wikipedia":
        return WikipediaBackend(lang=cfg.get("lang", "fr"))
    if sid == "searxng":
        instance = cfg.get("instance") or os.environ.get("SEARXNG_URL",
                                                          "http://localhost:8080")
        return SearxngBackend(instance=instance, lang=cfg.get("lang", "fr"))
    classe = _BACKENDS_WEB.get(sid)
    return classe() if classe else None


# --- Détection hors-ligne / config ----------------------------------------

def est_hors_ligne(hote="1.1.1.1", port=443, timeout=2.5) -> bool:
    try:
        with socket.create_connection((hote, port), timeout=timeout):
            return False
    except OSError:
        return True


def charger_config(chemin: str | Path | None = None) -> dict:
    if chemin is None:
        chemin = Path(__file__).with_name("sources.json")
    return json.loads(Path(chemin).read_text(encoding="utf-8"))


# --- 0.3  Orchestration ----------------------------------------------------

def collecter(question, config=None, fixtures=None, forcer_hors_ligne=False,
              recence=None, filtrer=True) -> dict:
    config = config or charger_config()
    parse = parser_question(question)
    requetes = generer_requetes(parse)
    plafond = config.get("plafond_sources_total", 20)

    resultats: list[dict] = []
    inaccessibles: list[dict] = []
    attempts: set[str] = set()
    vues: set[str] = set()

    def _ajouter(bruts, sid, r) -> int:
        n = 0
        for res in bruts:
            if len(resultats) >= plafond:
                break
            u = res.get("url", "")
            if not u or u in vues:
                continue
            vues.add(u)
            resultats.append({**res, "backend": sid,
                              "requete": r["requete"], "angle": r["angle"]})
            n += 1
        return n

    # --- Mode fixtures (test local hors-réseau) ------------------------
    if fixtures is not None:
        for r in requetes:
            _ajouter(fixtures.get(r["angle"], []), "fixtures", r)
        return _assembler(question, parse, requetes, resultats, inaccessibles,
                          ["fixtures"], hors_ligne=False, mode="fixtures",
                          filtrer=filtrer)

    # --- Mode réseau ---------------------------------------------------
    hors_ligne = forcer_hors_ligne or est_hors_ligne()
    cfg_par_id = {s["id"]: s for s in config.get("sources", []) if s.get("actif", True)}

    specialises, generalistes, enrichisseurs = [], [], []
    for sid, cfg in cfg_par_id.items():
        backend = _instancier(sid, cfg)
        if backend is None or not backend.condition_remplie(parse, cfg):
            continue
        if hors_ligne and not backend.local:
            inaccessibles.append({"backend": sid, "requete": "—", "raison": "hors-ligne"})
            continue
        if backend.role == "enrichissement":
            enrichisseurs.append((sid, cfg, backend))
        elif backend.role in ("specialise", "additif"):
            specialises.append((sid, cfg, backend))
        else:
            generalistes.append((cfg.get("priorite", 50), sid, cfg, backend))
    generalistes.sort(key=lambda x: x[0])

    for r in requetes:
        if len(resultats) >= plafond:
            break
        angle = r["angle"]

        # spécialisés : additifs
        for sid, cfg, backend in specialises:
            if angle not in backend.angles or len(resultats) >= plafond:
                continue
            attempts.add(sid)
            try:
                bruts = backend.rechercher(r["requete"], cfg.get("max_resultats", 5),
                                           angle, recence)
            except Exception as exc:
                inaccessibles.append({"backend": sid, "requete": r["requete"],
                                      "raison": f"[inaccessible] {exc}"[:200]})
                continue
            _ajouter(bruts, sid, r)

        # généralistes : chaîne de repli par priorité
        for _prio, sid, cfg, backend in generalistes:
            if angle not in backend.angles or len(resultats) >= plafond:
                continue
            attempts.add(sid)
            try:
                bruts = backend.rechercher(r["requete"], cfg.get("max_resultats", 5),
                                           angle, recence)
            except ImportError:
                inaccessibles.append({"backend": sid, "requete": r["requete"],
                                      "raison": "dépendance manquante (pip install ddgs)"})
                continue
            except Exception as exc:
                inaccessibles.append({"backend": sid, "requete": r["requete"],
                                      "raison": f"[inaccessible] {exc}"[:200]})
                continue
            if _ajouter(bruts, sid, r) > 0:
                break  # un généraliste a répondu : on n'interroge pas le repli

    # enrichisseurs (Wayback) : opèrent sur les résultats collectés, pas la requête
    for sid, cfg, backend in enrichisseurs:
        if not resultats:
            break
        attempts.add(sid)
        backend.enrichir(resultats)

    return _assembler(question, parse, requetes, resultats, inaccessibles,
                      sorted(attempts), hors_ligne, mode="reseau", filtrer=filtrer)


def _cle_date(r) -> str:
    """Clé de tri par fraîcheur. Les dates ISO se trient lexicalement ;
    les résultats sans date passent en dernier (chaîne vide)."""
    d = r.get("date")
    return str(d) if d else ""


# --- Filtre de pertinence par entités (pays + noms propres) ----------------
# Écarte les résultats qui ne mentionnent pas les entités propres de la question
# (un pays nommé, par ex.), pour éliminer le hors-sujet. Formes normalisées
# (minuscules, sans accents) : nom + gentilé + capitale pour les pays courants.

_PAYS_FORMES = {
    "france": {"france", "francais", "paris", "hexagone"},
    "iran": {"iran", "teheran"},
    "etats-unis": {"etats-unis", "etats unis", "americain", "usa", "washington"},
    "chine": {"chine", "chinois", "pekin", "beijing"},
    "russie": {"russie", "russe", "moscou"},
    "ukraine": {"ukraine", "ukrainien", "kiev", "kyiv"},
    "israel": {"israel", "israelien", "jerusalem", "tel-aviv"},
    "allemagne": {"allemagne", "allemand", "berlin"},
    "royaume-uni": {"royaume-uni", "royaume uni", "britannique", "anglais", "londres"},
    "inde": {"inde", "indien", "new delhi", "new-delhi"},
    "japon": {"japon", "japonais", "tokyo"},
    "coree-du-nord": {"coree du nord", "coree-du-nord", "nord-coreen", "pyongyang"},
    "coree-du-sud": {"coree du sud", "coree-du-sud", "sud-coreen", "seoul"},
    "arabie-saoudite": {"arabie saoudite", "arabie-saoudite", "saoudien", "ryad", "riyad"},
    "turquie": {"turquie", "turc", "turque", "ankara", "istanbul"},
    "syrie": {"syrie", "syrien", "damas"},
    "irak": {"irak", "irakien", "bagdad"},
    "egypte": {"egypte", "egyptien", "caire"},
    "bresil": {"bresil", "bresilien", "brasilia"},
    "italie": {"italie", "italien", "rome"},
    "espagne": {"espagne", "espagnol", "madrid"},
    "canada": {"canada", "canadien", "ottawa"},
    "mexique": {"mexique", "mexicain", "mexico"},
    "venezuela": {"venezuela", "venezuelien", "caracas"},
    "pakistan": {"pakistan", "pakistanais", "islamabad"},
    "afghanistan": {"afghanistan", "afghan", "kaboul"},
    "liban": {"liban", "libanais", "beyrouth"},
    "qatar": {"qatar", "qatari", "doha"},
    "emirats": {"emirats", "emirati", "abou dabi", "dubai"},
    "taiwan": {"taiwan", "taiwanais", "taipei"},
}

# Mots capitalisables fréquents à ne PAS traiter comme entités requises.
_ENTITES_STOP = {"crise", "marche", "marches", "dette", "economie", "banque",
                 "banques", "monde", "etat", "etats", "gouvernement", "rapport"}


def _norm(s: str) -> str:
    s = (s or "").lower()
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def _forme_dans(forme: str, texte_norm: str) -> bool:
    """texte_norm est déjà normalisé. Multi-mots -> sous-chaîne ; mot court (<=3)
    -> mot exact ; sinon -> préfixe de mot (capte gentilés : iran -> iranien)."""
    f = _norm(forme)
    if " " in f or "-" in f:
        return f in texte_norm
    if len(f) <= 3:
        return re.search(r"\b" + re.escape(f) + r"\b", texte_norm) is not None
    return re.search(r"\b" + re.escape(f) + r"[a-z]*", texte_norm) is not None


def _entites_requises(parse: dict, question: str) -> list[set]:
    """Ensembles de formes que tout résultat doit contenir (au moins une par set)."""
    qn = _norm(question)
    requis: list[set] = []
    couvert: set = set()
    for formes in _PAYS_FORMES.values():
        if any(_forme_dans(f, qn) for f in formes):
            fset = {_norm(f) for f in formes}
            requis.append(fset)
            couvert |= fset
    # noms propres génériques (pays non répertoriés, organisations, personnes)
    mots = question.split()
    premier = _norm(mots[0]) if mots else ""
    for e in parse.get("entites", []):
        en = _norm(e)
        if (not en or en == premier or len(en) <= 2 or en in _ENTITES_STOP
                or en in couvert or any(en in s for s in requis)):
            continue
        requis.append({en} | {w for w in en.split() if len(w) > 3})
    return requis


def _resultat_couvre(res: dict, requis: list[set], tous: bool) -> bool:
    texte = _norm((res.get("titre", "") + " " + res.get("extrait", "")))
    hits = [any(_forme_dans(f, texte) for f in s) for s in requis]
    return all(hits) if tous else any(hits)


def _filtrer_pertinence(resultats: list[dict], requis: list[set]):
    """Garde les résultats couvrant TOUTES les entités requises. Relâche à 'au
    moins une' si le strict vide tout, et ne supprime jamais l'intégralité."""
    if not requis or not resultats:
        return resultats, 0
    stricts = [r for r in resultats if _resultat_couvre(r, requis, True)]
    if stricts:
        return stricts, len(resultats) - len(stricts)
    souples = [r for r in resultats if _resultat_couvre(r, requis, False)]
    if souples:
        return souples, len(resultats) - len(souples)
    return resultats, 0  # garde-fou : ne jamais tout écarter


def _assembler(question, parse, requetes, resultats, inaccessibles,
               backends_actifs, hors_ligne, mode, filtrer=True) -> dict:
    ecartes = 0
    if filtrer:
        requis = _entites_requises(parse, question)
        resultats, ecartes = _filtrer_pertinence(resultats, requis)
    resultats = sorted(resultats, key=_cle_date, reverse=True)  # plus récent d'abord
    return {
        "question": question,
        "horodatage": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode_collecte": mode,
        "hors_ligne": hors_ligne,
        "parse": parse,
        "requetes": requetes,
        "backends_actifs": backends_actifs,
        "resultats": resultats,
        "hors_sujet_ecartes": ecartes,
        "inaccessibles": inaccessibles,
    }


if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv) > 1 else "crise financière marchés émergents 2027"
    print(json.dumps(collecter(q, forcer_hors_ligne=True), ensure_ascii=False, indent=2))

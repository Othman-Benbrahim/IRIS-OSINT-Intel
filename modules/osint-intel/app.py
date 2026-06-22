#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
app.py — Application OSINT-Intel : interface web locale unifiée.

Lance un serveur local, ouvre le navigateur, et expose TOUT le pipeline dans une
seule interface : Deep Research → validation → analyse → rapport, plus le mode
descendant. Aucune compilation, aucune ligne de commande pour l'utilisateur.

    python app.py            # démarre + ouvre http://127.0.0.1:8765
"""

from __future__ import annotations

import json
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_HERE = Path(__file__).resolve().parent           # modules/osint-intel
_ROOT = _HERE.parents[1]                           # IRIS-Standalone
for p in (_HERE, _HERE / "deep-research", _HERE / "validation", str(_ROOT)):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import search            # noqa: E402
import synthesizer       # noqa: E402
import analyse           # noqa: E402
import export            # noqa: E402
import validation_gate as vg  # noqa: E402
import mode_descendant   # noqa: E402
from run_analyse import _llm_demo  # noqa: E402

PORT = 8765
PROJET = _ROOT / "data" / "projets" / "courant"
PROJET.mkdir(parents=True, exist_ok=True)

# État de session (appli mono-utilisateur locale)
SESSION: dict = {"collecte": None, "corpus": None, "corpus_valide": None}
_SOURCES = _HERE / "deep-research" / "sources.json"


def _charger_sources() -> dict:
    return json.loads(_SOURCES.read_text(encoding="utf-8"))


def _sauver_sources(cfg: dict) -> None:
    _SOURCES.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def _liste_sources() -> dict:
    cfg = _charger_sources()
    return {"sources": [{"id": s["id"], "nom": s.get("nom", s["id"]),
                         "actif": s.get("actif", True), "type": s.get("type", ""),
                         "note": s.get("note", "")} for s in cfg.get("sources", [])]}


def action_sources(d: dict) -> dict:
    """Active/désactive des backends (POST). d = {'etats': {'gdelt': true, ...}}."""
    etats = d.get("etats", {})
    cfg = _charger_sources()
    for s in cfg.get("sources", []):
        if s["id"] in etats:
            s["actif"] = bool(etats[s["id"]])
    _sauver_sources(cfg)
    return _liste_sources()

# Beaucoup d'API (FantasyAI inclus) sont derrière un filtre anti-robot qui rejette
# le User-Agent par défaut de Python (403). On envoie un UA de navigateur normal.
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")


def _charger_llm_config() -> dict:
    f = _HERE / "llm.json"
    try:
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    except json.JSONDecodeError:
        return {}


def _llm(mode: str):
    cfg = _charger_llm_config()
    if mode == "ollama":
        import llm_adapters
        o = cfg.get("ollama", {})
        return llm_adapters.adaptateur_ollama(
            modele=o.get("modele", "llama3.1"), hote=o.get("hote", "http://localhost:11434"))
    if mode == "fantasyai":
        import llm_adapters
        fa = cfg.get("fantasyai", {})
        return llm_adapters.adaptateur_fantasyai(
            url=fa.get("url", ""), cle=fa.get("cle", ""), modele=fa.get("modele", "default"))
    if mode == "demo":
        return _llm_demo()
    return None  # extractif / aucun


def _sauver_llm_config(cfg: dict) -> None:
    (_HERE / "llm.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def _url_modeles(url_chat: str) -> str:
    base = url_chat or "https://fantasyai.cloud/api/v1/chat/completions"
    if base.endswith("/chat/completions"):
        return base[: -len("/chat/completions")] + "/models"
    return base.rstrip("/") + "/models"


def _cle_source(sid: str) -> str:
    try:
        for s in _charger_sources().get("sources", []):
            if s.get("id") == sid:
                return s.get("cle", "") or ""
    except Exception:
        pass
    return ""


def _config_publique(cfg: dict) -> dict:
    """Config renvoyée à l'interface — les clés sont masquées, jamais en clair."""
    fa = cfg.get("fantasyai", {})
    cle = fa.get("cle", "")
    definie = bool(cle) and cle != "COLLE-TA-CLÉ-API-ICI"

    def _statut(sid):
        c = _cle_source(sid)
        ok = bool(c) and c != "COLLE-TA-CLÉ-API-ICI"
        return {"cle_definie": ok,
                "cle_apercu": ("…" + c[-4:]) if ok and len(c) >= 4 else ""}

    return {"fantasyai": {"cle_definie": definie,
                          "cle_apercu": ("…" + cle[-4:]) if definie and len(cle) >= 4 else "",
                          "modele": fa.get("modele", ""),
                          "url": fa.get("url", "")},
            "ollama": {"modele": cfg.get("ollama", {}).get("modele", "")},
            "tavily": _statut("tavily"),
            "exa": _statut("exa")}


def action_config(d: dict) -> dict:
    """Enregistre clé / modèle (et change si on change). Persisté dans llm.json."""
    cfg = _charger_llm_config()
    fa = cfg.setdefault("fantasyai", {})
    if "fantasyai_cle" in d:
        fa["cle"] = (d["fantasyai_cle"] or "").strip()
    if "fantasyai_modele" in d:
        fa["modele"] = d["fantasyai_modele"]
    if d.get("fantasyai_url", "").strip():
        fa["url"] = d["fantasyai_url"].strip()
    if "ollama_modele" in d:
        cfg.setdefault("ollama", {})["modele"] = d["ollama_modele"]
    _sauver_llm_config(cfg)
    # clés des sources de recherche -> stockées dans sources.json
    cles_sources = {"tavily_cle": "tavily", "exa_cle": "exa"}
    if any(k in d for k in cles_sources):
        scfg = _charger_sources()
        for champ, sid in cles_sources.items():
            if champ in d:
                for s in scfg.get("sources", []):
                    if s.get("id") == sid:
                        s["cle"] = (d[champ] or "").strip()
                        break
        _sauver_sources(scfg)
    return {"ok": True, "config": _config_publique(cfg)}


def action_modeles(d: dict) -> dict:
    """Charge la liste des modèles FantasyAI avec la clé enregistrée."""
    import urllib.error
    import urllib.request
    cfg = _charger_llm_config()
    fa = cfg.setdefault("fantasyai", {})
    if d.get("cle"):  # permet d'enregistrer la clé au moment du chargement
        fa["cle"] = d["cle"].strip()
        _sauver_llm_config(cfg)
    cle = fa.get("cle", "")
    if not cle or cle == "COLLE-TA-CLÉ-API-ICI":
        return {"erreur": "Enregistre d'abord ta clé API FantasyAI."}
    url = _url_modeles(fa.get("url", ""))
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {cle}",
        "Accept": "application/json",
        "User-Agent": _UA,
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as rep:
            data = json.loads(rep.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            corps = e.read().decode("utf-8", "ignore")[:300]
        except Exception:
            corps = ""
        if e.code == 401:
            msg = "clé refusée (401) — vérifie la clé."
        elif e.code == 403:
            msg = f"accès refusé (403) — requête bloquée ou droit manquant. {corps}"
        elif e.code == 429:
            msg = "trop de requêtes (429) — réessaie dans un moment."
        else:
            msg = f"erreur {e.code}. {corps}"
        return {"erreur": "FantasyAI : " + msg}
    except Exception as e:
        return {"erreur": f"Impossible de joindre FantasyAI ({type(e).__name__})."}
    brut = data.get("data", data) if isinstance(data, dict) else data
    modeles = sorted(m.get("id") if isinstance(m, dict) else m
                     for m in (brut or []) if (m.get("id") if isinstance(m, dict) else m))
    return {"modeles": modeles, "selection": fa.get("modele", "")}


# --- Actions du pipeline ---------------------------------------------------

def action_recherche(d: dict) -> dict:
    question = (d.get("question") or "").strip()
    if not question:
        return {"erreur": "Pose une question d'abord."}
    fixtures = None
    if d.get("recherche") == "fixtures":
        import fixtures as fx
        fixtures = fx.FIXTURES_CRISE_EMERGENTS
    collecte = search.collecter(question, fixtures=fixtures,
                                forcer_hors_ligne=bool(d.get("hors_ligne")),
                                recence=d.get("recence"),
                                filtrer=d.get("filtrer", True))
    synth_llm = _llm(d.get("synthese", "extractive")) if d.get("synthese") == "llm" else None
    corpus = synthesizer.synthetiser(collecte, llm=synth_llm)
    SESSION.update(collecte=collecte, corpus=corpus, corpus_valide=None)
    md = synthesizer.corpus_vers_md(collecte, corpus)
    (PROJET / "corpus.md").write_text(md, encoding="utf-8")
    par_backend = {b: 0 for b in collecte["backends_actifs"]}
    for r in collecte["resultats"]:
        par_backend[r.get("backend", "?")] = par_backend.get(r.get("backend", "?"), 0) + 1
    return {
        "question": question,
        "hors_ligne": collecte["hors_ligne"],
        "stats": {"total": len(corpus["assertions"]),
                  "fiabilite": corpus["fiabilite_globale"],
                  "backends": collecte["backends_actifs"],
                  "hors_sujet": collecte.get("hors_sujet_ecartes", 0),
                  "inaccessibles": len(collecte["inaccessibles"])},
        "par_backend": par_backend,
        "inaccessibles_detail": [
            {"backend": x.get("backend"), "raison": x.get("raison")}
            for x in collecte["inaccessibles"]],
        "sources": [{"url": a.get("url"), "extrait": a.get("texte"),
                     "fiabilite": a.get("fiabilite"), "backend": a.get("backend"),
                     "archive_url": a.get("archive_url"), "date": a.get("date"),
                     "corrobore": a.get("corrobore", False)}
                    for a in corpus["assertions"]],
    }


def action_analyser(d: dict) -> dict:
    if not SESSION.get("corpus"):
        return {"erreur": "Lance d'abord une recherche."}
    gardees = d.get("gardees", [])
    ajouts = d.get("ajouts", [])
    cv = vg.appliquer_validation(SESSION["corpus"], gardees, ajouts)
    vg.ecrire_corpus_valide(cv, PROJET / "corpus-valide.md")
    SESSION["corpus_valide"] = cv

    mode = d.get("llm", "demo")
    llm = _llm(mode)
    if llm is None:
        return {"erreur": "Choisis un moteur d'analyse (Ollama, FantasyAI ou Démo)."}
    try:
        resultat = analyse.analyser(cv, llm=llm)
        chemin = export.exporter(resultat, PROJET / "rapport-osint.md")
    except Exception as e:
        return {"erreur": f"Analyse impossible : {e}"}
    texte = Path(chemin).read_text(encoding="utf-8")
    return {"ok": True, "chemin": str(chemin),
            "resume": {"hypotheses": len(resultat["hypotheses"]),
                       "scenarios": len(resultat["scenarios"]),
                       "predictions": len(resultat["predictions"]),
                       "gardees": cv["validation"]["gardees"],
                       "rejetees": cv["validation"]["rejetees"],
                       "ajouts": cv["validation"]["ajouts_manuels"]},
            "rapport": texte}


def action_descendant(d: dict) -> dict:
    contenu = d.get("contenu", "")
    if not contenu.strip():
        return {"erreur": "Colle un rapport IRIS/Yggdrasil à re-challenger."}
    entree_path = PROJET / "entree-source.md"
    entree_path.write_text(contenu, encoding="utf-8")
    llm = _llm(d.get("llm", "demo"))
    if llm is None:
        return {"erreur": "Choisis un moteur (Ollama, FantasyAI ou Démo)."}
    fixtures = None
    if d.get("recherche") == "fixtures":
        import fixtures as fx
        fixtures = fx.FIXTURES_CRISE_EMERGENTS
    try:
        chemin = mode_descendant.re_challenger_fichier(
            entree_path, PROJET / "rapport-rechallenge.md", llm, fixtures=fixtures)
    except Exception as e:
        return {"erreur": f"Re-challenge impossible : {e}"}
    return {"ok": True, "chemin": str(chemin),
            "rapport": Path(chemin).read_text(encoding="utf-8")}


_ROUTES = {
    "/api/recherche": action_recherche,
    "/api/analyser": action_analyser,
    "/api/descendant": action_descendant,
    "/api/config": action_config,
    "/api/modeles": action_modeles,
    "/api/sources": action_sources,
}


# --- Serveur ---------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def _envoyer(self, code, charge, ctype="application/json; charset=utf-8", brut=False):
        corps = charge if brut else json.dumps(charge, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._envoyer(200, (_HERE / "interface.html").read_bytes(),
                          "text/html; charset=utf-8", brut=True)
        elif self.path == "/api/config":
            self._envoyer(200, _config_publique(_charger_llm_config()))
        elif self.path == "/api/sources":
            self._envoyer(200, _liste_sources())
        else:
            self._envoyer(404, {"erreur": "introuvable"})

    def do_POST(self):
        action = _ROUTES.get(self.path)
        if not action:
            self._envoyer(404, {"erreur": "introuvable"})
            return
        taille = int(self.headers.get("Content-Length", 0))
        try:
            d = json.loads(self.rfile.read(taille).decode("utf-8")) if taille else {}
        except json.JSONDecodeError:
            self._envoyer(400, {"erreur": "données invalides"})
            return
        try:
            self._envoyer(200, action(d))
        except Exception as e:  # filet de sécurité
            self._envoyer(500, {"erreur": f"{type(e).__name__} : {e}"})

    def log_message(self, *a):
        pass


def demarrer(ouvrir=True):
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}"
    print(f"\n  OSINT-Intel est lancé.\n  Ouvre ton navigateur sur : {url}\n"
          f"  (Ctrl+C pour arrêter)\n")
    if ouvrir:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Arrêt.")
        srv.shutdown()


if __name__ == "__main__":
    demarrer(ouvrir="--no-open" not in sys.argv)

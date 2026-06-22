#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
exchange_format.py — Contrat d'interface de l'écosystème IRIS∞.

Schéma, parseur et validateur du format d'échange « YAML front matter ».
Tous les modules (OSINT-Intel, IRIS-Station, Yggdrasil) communiquent via un
fichier .md commençant par un bloc YAML délimité par `---`.

Deux sens de validation :
  - SORTIE (source = osint-intel) : ce que produit OSINT-Intel.
  - ENTRÉE (source = iris-station | yggdrasil) : mode descendant, ce
    qu'OSINT-Intel reçoit pour re-challenger un rapport existant.

Usage CLI :
    python exchange_format.py rapport.md [autre.md ...]
    python exchange_format.py --strict rapport.md   # avertissements = erreurs

Code de sortie : 0 si tout est conforme, 1 si au moins une erreur.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "Dépendance manquante : PyYAML. Installez-la avec `pip install pyyaml`.\n"
    )
    raise

SCHEMA_VERSION = "1.0"

# --- Vocabulaire contrôlé -------------------------------------------------

SOURCES_SORTIE = {"osint-intel"}
SOURCES_ENTREE = {"iris-station", "yggdrasil"}
MODES = {"express", "complet", "prospectif", "profilage"}
TYPES_HYPOTHESE = {"dominante", "dissidente", "fractale"}
TYPES_PREDICTION = {"binaire", "numerique", "categorielle", "date"}
SIGNIFICANCES = {"haute", "moyenne", "basse"}
DIRECTIONS = {"↑", "↓", "↗", "↘", "→", "↔", "∅"}

PROB_MIN, PROB_MAX = 0.05, 0.95
SOMME_SCENARIOS_TOL = 0.02  # les scénarios sont exhaustifs : leur somme ≈ 1.0


# --- Collecteur de diagnostics --------------------------------------------

class Rapport:
    """Accumule erreurs et avertissements, chacun avec son chemin."""

    def __init__(self) -> None:
        self.erreurs: list[tuple[str, str]] = []
        self.avertissements: list[tuple[str, str]] = []

    def erreur(self, chemin: str, message: str) -> None:
        self.erreurs.append((chemin, message))

    def avertissement(self, chemin: str, message: str) -> None:
        self.avertissements.append((chemin, message))

    @property
    def ok(self) -> bool:
        return not self.erreurs


class ErreurFormat(Exception):
    """YAML malformé ou bloc d'échange introuvable."""


# --- Helpers de validation -------------------------------------------------

def _est_nombre(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _exiger(rapport: Rapport, conteneur, cle: str, chemin: str, type_attendu=None):
    """Vérifie la présence d'une clé ; renvoie la valeur ou None."""
    if not isinstance(conteneur, dict) or cle not in conteneur:
        rapport.erreur(f"{chemin}.{cle}", "champ obligatoire absent")
        return None
    val = conteneur[cle]
    if type_attendu is not None and not isinstance(val, type_attendu):
        attendu = type_attendu.__name__
        rapport.erreur(f"{chemin}.{cle}", f"type invalide (attendu : {attendu})")
        return None
    return val


def _verifier_proba(rapport: Rapport, valeur, chemin: str) -> None:
    if not _est_nombre(valeur):
        rapport.erreur(chemin, "probabilité non numérique")
        return
    if not (PROB_MIN <= valeur <= PROB_MAX):
        rapport.erreur(
            chemin,
            f"probabilité {valeur} hors bornes [{PROB_MIN}, {PROB_MAX}] "
            f"(jamais 0 ni 1 : l'incertitude est toujours assumée)",
        )


def _verifier_enum(rapport: Rapport, valeur, chemin: str, valeurs: set, dur: bool = True) -> None:
    if valeur not in valeurs:
        msg = f"valeur '{valeur}' hors vocabulaire {sorted(valeurs)}"
        (rapport.erreur if dur else rapport.avertissement)(chemin, msg)


def _verifier_timestamp(rapport: Rapport, valeur, chemin: str) -> None:
    if not isinstance(valeur, str):
        rapport.erreur(chemin, "timestamp non textuel")
        return
    try:
        datetime.fromisoformat(valeur.replace("Z", "+00:00"))
    except ValueError:
        rapport.erreur(chemin, f"timestamp ISO 8601 invalide : '{valeur}'")


# --- Lecture du fichier ----------------------------------------------------

def extraire_front_matter(texte: str) -> str:
    """Extrait le bloc YAML d'un .md (entre `---`).
    Si le texte ne commence pas par `---`, il est interprété comme YAML pur."""
    texte = texte.lstrip("\ufeff")  # BOM éventuel
    lignes = texte.splitlines()
    if not lignes or lignes[0].strip() != "---":
        return texte
    for i in range(1, len(lignes)):
        if lignes[i].strip() in ("---", "..."):
            return "\n".join(lignes[1:i])
    raise ErreurFormat("Front matter ouvert par `---` mais jamais refermé par `---`.")


def charger(source) -> dict:
    """Charge un document d'échange depuis un chemin ou une chaîne.
    Renvoie le dict complet (avec la clé `iris_exchange`).
    Lève ErreurFormat si le YAML est malformé."""
    if isinstance(source, (str, Path)) and Path(str(source)).exists():
        texte = Path(source).read_text(encoding="utf-8")
    else:
        texte = str(source)
    front = extraire_front_matter(texte)
    try:
        doc = yaml.safe_load(front)
    except yaml.YAMLError as exc:
        raise ErreurFormat(f"YAML malformé : {exc}") from exc
    if not isinstance(doc, dict):
        raise ErreurFormat("Le document ne contient pas de mapping YAML en tête.")
    return doc


# --- En-tête commune -------------------------------------------------------

def _valider_entete(rapport: Rapport, ex: dict):
    version = _exiger(rapport, ex, "version", "iris_exchange", str)
    if version is not None and version != SCHEMA_VERSION:
        rapport.avertissement(
            "iris_exchange.version",
            f"version '{version}' ≠ version supportée '{SCHEMA_VERSION}'",
        )
    source = _exiger(rapport, ex, "source", "iris_exchange", str)
    ts = _exiger(rapport, ex, "timestamp", "iris_exchange", str)
    if ts is not None:
        _verifier_timestamp(rapport, ts, "iris_exchange.timestamp")
    _exiger(rapport, ex, "session_id", "iris_exchange", str)
    return source


# --- Validation SORTIE (osint-intel) --------------------------------------

def _valider_sortie(rapport: Rapport, ex: dict) -> None:
    _exiger(rapport, ex, "question_intelligence", "iris_exchange", str)

    mode = _exiger(rapport, ex, "mode", "iris_exchange", str)
    if mode is not None:
        _verifier_enum(rapport, mode, "iris_exchange.mode", MODES)

    dru = ex.get("deep_research_used")
    if dru is not None and not isinstance(dru, bool):
        rapport.erreur("iris_exchange.deep_research_used", "booléen attendu")

    # --- hypotheses : ≥ 3, priors bornés -------------------------------
    hyps = _exiger(rapport, ex, "hypotheses", "iris_exchange", list)
    if isinstance(hyps, list):
        if len(hyps) < 3:
            rapport.erreur(
                "iris_exchange.hypotheses",
                f"au moins 3 hypothèses requises (trouvé : {len(hyps)})",
            )
        somme = 0.0
        for i, h in enumerate(hyps):
            c = f"iris_exchange.hypotheses[{i}]"
            if not isinstance(h, dict):
                rapport.erreur(c, "élément attendu de type mapping")
                continue
            _exiger(rapport, h, "id", c, str)
            _exiger(rapport, h, "name", c, str)
            p = _exiger(rapport, h, "probability_prior", c)
            if p is not None:
                _verifier_proba(rapport, p, f"{c}.probability_prior")
                if _est_nombre(p):
                    somme += p
            t = _exiger(rapport, h, "type", c, str)
            if t is not None:
                _verifier_enum(rapport, t, f"{c}.type", TYPES_HYPOTHESE)
        if hyps and abs(somme - 1.0) > 0.05:
            rapport.avertissement(
                "iris_exchange.hypotheses",
                f"somme des priors = {round(somme, 3)} (≠ 1.0 : normal si les "
                f"hypothèses ne sont pas exhaustives)",
            )

    # --- scenarios : exhaustifs → somme ≈ 1.0 --------------------------
    scs = _exiger(rapport, ex, "scenarios", "iris_exchange", list)
    if isinstance(scs, list):
        somme = 0.0
        for i, s in enumerate(scs):
            c = f"iris_exchange.scenarios[{i}]"
            if not isinstance(s, dict):
                rapport.erreur(c, "élément attendu de type mapping")
                continue
            _exiger(rapport, s, "id", c, str)
            _exiger(rapport, s, "name", c, str)
            p = _exiger(rapport, s, "probability", c)
            if p is not None:
                _verifier_proba(rapport, p, f"{c}.probability")
                if _est_nombre(p):
                    somme += p
            _exiger(rapport, s, "indicators", c, list)
        if scs and abs(somme - 1.0) > SOMME_SCENARIOS_TOL:
            rapport.erreur(
                "iris_exchange.scenarios",
                f"somme des probabilités = {round(somme, 3)} ; les scénarios "
                f"doivent être exhaustifs (somme ≈ 1.0, tolérance ±{SOMME_SCENARIOS_TOL})",
            )

    # --- predictions ---------------------------------------------------
    preds = _exiger(rapport, ex, "predictions", "iris_exchange", list)
    if isinstance(preds, list):
        for i, p in enumerate(preds):
            c = f"iris_exchange.predictions[{i}]"
            if not isinstance(p, dict):
                rapport.erreur(c, "élément attendu de type mapping")
                continue
            _exiger(rapport, p, "id", c, str)
            _exiger(rapport, p, "question", c, str)
            pr = _exiger(rapport, p, "probability", c)
            if pr is not None:
                _verifier_proba(rapport, pr, f"{c}.probability")
            t = p.get("type")
            if t is not None:
                _verifier_enum(rapport, t, f"{c}.type", TYPES_PREDICTION, dur=False)
            _exiger(rapport, p, "horizon", c)

    # --- signaux_faibles (optionnel, structuré si présent) -------------
    sigs = ex.get("signaux_faibles")
    if sigs is not None:
        if not isinstance(sigs, list):
            rapport.erreur("iris_exchange.signaux_faibles", "liste attendue")
        else:
            for i, s in enumerate(sigs):
                c = f"iris_exchange.signaux_faibles[{i}]"
                if not isinstance(s, dict):
                    rapport.erreur(c, "élément attendu de type mapping")
                    continue
                _exiger(rapport, s, "signal", c, str)
                d = s.get("direction")
                if d is not None:
                    _verifier_enum(rapport, d, f"{c}.direction", DIRECTIONS, dur=False)
                sg = s.get("significance")
                if sg is not None:
                    _verifier_enum(rapport, sg, f"{c}.significance", SIGNIFICANCES, dur=False)

    # --- sources (bloc statistique) ------------------------------------
    src = _exiger(rapport, ex, "sources", "iris_exchange", dict)
    if isinstance(src, dict):
        for champ in ("total", "deep_research", "manuelles"):
            v = src.get(champ)
            if v is None:
                rapport.erreur(f"iris_exchange.sources.{champ}", "champ obligatoire absent")
            elif not isinstance(v, int) or isinstance(v, bool):
                rapport.erreur(f"iris_exchange.sources.{champ}", "entier attendu")
        fm = src.get("fiabilite_moyenne")
        if fm is not None and (not _est_nombre(fm) or not (1 <= fm <= 5)):
            rapport.erreur(
                "iris_exchange.sources.fiabilite_moyenne",
                "fiabilité moyenne attendue dans [1, 5]",
            )
        t, dr, ma = src.get("total"), src.get("deep_research"), src.get("manuelles")
        if all(isinstance(x, int) and not isinstance(x, bool) for x in (t, dr, ma)):
            if t != dr + ma:
                rapport.avertissement(
                    "iris_exchange.sources",
                    f"total ({t}) ≠ deep_research ({dr}) + manuelles ({ma})",
                )

    # --- pour_iris_station (le handoff — recommandé) -------------------
    if "pour_iris_station" not in ex:
        rapport.avertissement(
            "iris_exchange.pour_iris_station",
            "bloc de transmission vers IRIS-Station absent (recommandé)",
        )


# --- Validation ENTRÉE (mode descendant) ----------------------------------

def _valider_entree(rapport: Rapport, ex: dict) -> None:
    hf = _exiger(rapport, ex, "hypotheses_formalisees", "iris_exchange", list)
    if isinstance(hf, list):
        for i, h in enumerate(hf):
            c = f"iris_exchange.hypotheses_formalisees[{i}]"
            if not isinstance(h, dict):
                rapport.erreur(c, "élément attendu de type mapping")
                continue
            _exiger(rapport, h, "id", c, str)
            _exiger(rapport, h, "name", c, str)
            phe = _exiger(rapport, h, "p_h_e", c)
            if phe is not None:
                _verifier_proba(rapport, phe, f"{c}.p_h_e")
            fb = h.get("facteur_bayes")
            if fb is not None and (not _est_nombre(fb) or fb <= 0):
                rapport.erreur(f"{c}.facteur_bayes", "facteur de Bayes > 0 attendu")

    aoi = _exiger(rapport, ex, "a_osint_intel", "iris_exchange", dict)
    if isinstance(aoi, dict):
        _exiger(rapport, aoi, "action", "iris_exchange.a_osint_intel", str)
        foc = aoi.get("focus")
        if foc is not None and not isinstance(foc, list):
            rapport.erreur("iris_exchange.a_osint_intel.focus", "liste attendue")
        q = aoi.get("questions")
        if q is not None and not isinstance(q, list):
            rapport.erreur("iris_exchange.a_osint_intel.questions", "liste attendue")

    cal = ex.get("calibration")
    if isinstance(cal, dict):
        b = cal.get("brier")
        if b is not None and (not _est_nombre(b) or not (0 <= b <= 1)):
            rapport.erreur("iris_exchange.calibration.brier", "Brier attendu dans [0, 1]")


# --- Point d'entrée logique ------------------------------------------------

def valider(doc: dict) -> Rapport:
    rapport = Rapport()
    ex = doc.get("iris_exchange")
    if ex is None:
        rapport.erreur("iris_exchange", "bloc racine 'iris_exchange' absent")
        return rapport
    if not isinstance(ex, dict):
        rapport.erreur("iris_exchange", "le bloc 'iris_exchange' doit être un mapping")
        return rapport
    source = _valider_entete(rapport, ex)
    if source in SOURCES_SORTIE:
        _valider_sortie(rapport, ex)
    elif source in SOURCES_ENTREE:
        _valider_entree(rapport, ex)
    elif source is not None:
        rapport.erreur(
            "iris_exchange.source",
            f"source inconnue '{source}' ; attendu : "
            f"{sorted(SOURCES_SORTIE | SOURCES_ENTREE)}",
        )
    return rapport


def charger_et_valider(source) -> Rapport:
    try:
        doc = charger(source)
    except ErreurFormat as exc:
        r = Rapport()
        r.erreur("(fichier)", str(exc))
        return r
    return valider(doc)


# --- CLI -------------------------------------------------------------------

def _afficher(nom: str, rapport: Rapport, strict: bool) -> bool:
    erreurs = list(rapport.erreurs)
    if strict:
        erreurs += rapport.avertissements
    if not erreurs:
        if rapport.avertissements:
            print(f"✅ {nom} — conforme ({len(rapport.avertissements)} avertissement(s))")
            for chemin, msg in rapport.avertissements:
                print(f"     ⚠  {chemin} : {msg}")
        else:
            print(f"✅ {nom} — conforme")
        return True
    print(f"❌ {nom} — {len(erreurs)} erreur(s)")
    for chemin, msg in rapport.erreurs:
        print(f"     ✗  {chemin} : {msg}")
    if strict:
        for chemin, msg in rapport.avertissements:
            print(f"     ✗  {chemin} : {msg}  [strict]")
    else:
        for chemin, msg in rapport.avertissements:
            print(f"     ⚠  {chemin} : {msg}")
    return False


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Validateur du format d'échange IRIS∞ (YAML front matter)."
    )
    parser.add_argument("fichiers", nargs="+", help="fichiers .md ou .yaml à valider")
    parser.add_argument(
        "--strict", action="store_true",
        help="traite les avertissements comme des erreurs",
    )
    args = parser.parse_args(argv)

    tout_ok = True
    for f in args.fichiers:
        ok = _afficher(f, charger_et_valider(f), args.strict)
        tout_ok = tout_ok and ok
    return 0 if tout_ok else 1


if __name__ == "__main__":
    sys.exit(main())

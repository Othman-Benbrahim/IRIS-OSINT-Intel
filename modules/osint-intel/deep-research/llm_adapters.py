#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm_adapters.py — Adaptateurs LLM pour la synthèse (étape 0.4).

Le synthétiseur attend un simple callable `str -> str` (prompt -> réponse texte).
Ce fichier fournit deux fabriques prêtes à brancher, conformes au switch
« local / cloud » des préférences.

Usage :
    from llm_adapters import adaptateur_ollama, adaptateur_fantasyai
    from synthesizer import synthetiser

    llm = adaptateur_ollama(modele="llama3.1")          # local
    # ou
    llm = adaptateur_fantasyai(url="https://...", cle="...")   # cloud

    corpus = synthetiser(collecte, llm=llm)

Aucun appel réseau n'est fait à l'import : la fabrique renvoie une fonction.
"""

from __future__ import annotations

import json
import urllib.request


def adaptateur_ollama(modele: str = "llama3.1",
                      hote: str = "http://localhost:11434",
                      timeout: int = 120):
    """LLM local via Ollama (http://localhost:11434)."""
    def appeler(prompt: str) -> str:
        import urllib.error
        corps = json.dumps({
            "model": modele,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{hote}/api/generate", data=corps,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as rep:
                brut = rep.read().decode("utf-8", "ignore")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama injoignable ({e.reason}) — est-il lancé "
                               f"sur {hote} ?")
        try:
            data = json.loads(brut)
        except json.JSONDecodeError:
            raise RuntimeError(f"Ollama a renvoyé une réponse non-JSON : {brut[:200]}")
        return data.get("response", "")
    return appeler


def adaptateur_fantasyai(url: str, cle: str, modele: str = "default",
                         timeout: int = 120):
    """LLM cloud (FantasyAI ou tout endpoint compatible « chat completions »).

    Adapter `url`, l'en-tête d'auth et le format de réponse à l'API réelle :
    les valeurs ci-dessous suivent la convention OpenAI-like la plus courante.
    """
    def appeler(prompt: str) -> str:
        import urllib.error
        corps = json.dumps({
            "model": modele,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            url, data=corps,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {cle}",
                "Accept": "application/json",
                "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/122.0 Safari/537.36"),
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as rep:
                brut = rep.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "ignore")[:300]
            except Exception:
                pass
            raise RuntimeError(f"FantasyAI HTTP {e.code} : {detail or e.reason}")
        if not brut.strip():
            raise RuntimeError("FantasyAI a renvoyé une réponse vide.")
        try:
            data = json.loads(brut)
        except json.JSONDecodeError:
            raise RuntimeError(f"FantasyAI a renvoyé une réponse non-JSON "
                               f"(modèle '{modele}' valide ?) : {brut[:300]}")
        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(f"FantasyAI erreur : {data['error']}")
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            raise RuntimeError(f"Réponse FantasyAI inattendue : {json.dumps(data)[:300]}")
    return appeler

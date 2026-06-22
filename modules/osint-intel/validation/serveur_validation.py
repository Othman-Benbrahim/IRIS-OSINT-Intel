#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
serveur_validation.py — Sidecar HTTP local de la barrière de validation.

C'est le processus que Tauri lancera (sidecar) ; la webview charge http://127.0.0.1:PORT.
En développement, on l'exécute seul et on ouvre l'URL dans un navigateur.

Endpoints :
  GET  /            -> panneau.html
  GET  /api/corpus  -> {question, stats, sources:[...]}
  POST /api/valider -> {gardees:[url], ajouts:[{...}]} -> écrit corpus-valide.md

Bibliothèque standard uniquement (aucune dépendance).

    python serveur_validation.py --corpus corpus.md --out corpus-valide.md --port 8765
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import validation_gate as vg

ETAT = {"corpus": None, "out": "corpus-valide.md"}
RACINE = Path(__file__).parent


class Handler(BaseHTTPRequestHandler):
    def _json(self, code, charge):
        corps = json.dumps(charge, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        if self.path in ("/", "/index.html", "/panneau.html"):
            page = (RACINE / "panneau.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            self.wfile.write(page)
        elif self.path == "/api/corpus":
            c = ETAT["corpus"]
            self._json(200, {"stats": vg.statistiques(c),
                             "sources": vg.sources_a_valider(c)})
        else:
            self._json(404, {"erreur": "introuvable"})

    def do_POST(self):
        if self.path != "/api/valider":
            self._json(404, {"erreur": "introuvable"})
            return
        taille = int(self.headers.get("Content-Length", 0))
        try:
            data = json.loads(self.rfile.read(taille).decode("utf-8"))
        except json.JSONDecodeError:
            self._json(400, {"erreur": "JSON invalide"})
            return
        gardees = data.get("gardees", [])
        ajouts = data.get("ajouts", [])
        valide = vg.appliquer_validation(ETAT["corpus"], gardees, ajouts)
        chemin = vg.ecrire_corpus_valide(valide, ETAT["out"])
        self._json(200, {"ok": True, "chemin": chemin,
                         "validation": valide["validation"]})

    def log_message(self, *a):  # silence
        pass


def main(argv=None):
    p = argparse.ArgumentParser(description="Sidecar de validation (Phase 3)")
    p.add_argument("--corpus", required=True, help="corpus.md de la Phase 2")
    p.add_argument("--out", default="corpus-valide.md")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--host", default="127.0.0.1")
    args = p.parse_args(argv)

    ETAT["corpus"] = vg.charger_corpus(args.corpus)
    ETAT["out"] = args.out
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Barrière de validation : http://{args.host}:{args.port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()

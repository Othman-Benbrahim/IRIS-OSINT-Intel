# Intégration des trois branches IRIS∞

Le launcher ne fusionne pas les branches : il les rassemble. Chaque branche est
indépendante et ne connaît que le **contrat d'échange** (`shared/exchange_format.py`)
et la **base partagée** (`shared/findings_cross/`).

## Principe

```
        OSINT-Intel (terrain)            IRIS-Station (labo)          Yggdrasil (exploration)
        acquisition + triage     →       formalisation ACH,    →      arbre des possibles,
        hypothèses brutes                Bayes, calibration            bifurcations, vigie
              │                                  │                            │
              └──────────── rapport .md (YAML front matter) ─────────────────┘
                         contrat unique : shared/exchange_format.py
```

- **Sens montant** : OSINT-Intel produit `rapport-osint.md` → importé par IRIS-Station.
- **Sens descendant** : un rapport IRIS/Yggdrasil (bloc `a_osint_intel`) → re-challengé
  par OSINT-Intel (`run_descendant.py`) → ressort au même format.

## Ce que chaque branche doit respecter

1. **Lire/écrire** uniquement via `shared/exchange_format.py` (valider avant d'émettre).
2. **Servir son UI** sur un port local distinct (sidecar) :
   OSINT-Intel `8765`, IRIS-Station `8780`, Yggdrasil `8790` (modifiable).
3. **Ne pas dupliquer** le niveau de l'autre : OSINT reste terrain (Bayes simple,
   Brier unitaire) ; le formel (ACH, Murphy, graphe) appartient à IRIS-Station.

## Brancher une nouvelle branche dans le launcher

1. La branche expose un sidecar HTTP local (même patron que
   `modules/osint-intel/validation/serveur_validation.py`).
2. Ajouter son port dans `iris-launcher/index.html` (carte de branche).
3. La déclarer en `externalBin` dans `iris-launcher/src-tauri/tauri.conf.json`
   (binaire figé PyInstaller) pour le packaging.

## Base de connaissances partagée

`shared/findings_cross/findings-cross-projets.md` recueille les constats
transverses (entités récurrentes, signaux vus dans plusieurs projets). Chaque
branche peut y lire et y ajouter — c'est le seul état partagé hors fichiers d'échange.

## Packaging

Compiler le launcher : `cd iris-launcher/src-tauri && cargo tauri build`.
Chaque sidecar Python est figé (PyInstaller) et embarqué via `externalBin`.
Résultat : une application de bureau unique pour les trois branches.

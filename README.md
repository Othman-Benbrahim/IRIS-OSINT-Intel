# IRIS∞ — OSINT-Intel

> Branche **« renseignement de terrain »** de l'écosystème IRIS∞.
> Un outil **local** d'OSINT et d'analyse prospective : collecte multi-moteurs →
> validation humaine → analyse terrain → rapport structuré réutilisable.

OSINT-Intel transforme une question d'intelligence en un corpus sourcé, le soumet à
votre validation, puis produit une note d'analyse (hypothèses, scénarios, signaux
faibles, risques) exportée dans un format d'échange standardisé. Tout se pilote
depuis une **interface web locale** — aucune ligne de commande, aucune compilation.

---

## Sommaire

- [Présentation](#présentation)
- [Pipeline](#pipeline)
- [Installation et lancement](#installation-et-lancement)
- [Configuration (clés API)](#configuration-clés-api)
- [Moteurs de recherche](#moteurs-de-recherche)
- [Utilisation](#utilisation)
- [Format d'échange](#format-déchange-contrat-dinterface)
- [Arborescence](#arborescence)
- [Limitations connues](#limitations-connues)
- [Écosystème IRIS∞](#écosystème-iris)
- [État du projet](#état-du-projet)
- [Licence](#licence)

---

## Présentation

OSINT-Intel est la **3ᵉ branche** d'IRIS∞, aux côtés d'IRIS-Station (laboratoire) et
Yggdrasil (exploration). Son rôle est celui du **terrain** : acquérir, trier, et
formuler des hypothèses brutes — pas formaliser ni calibrer.

| OSINT-Intel **fait** | OSINT-Intel **délègue** (→ IRIS-Station) |
|---|---|
| Collecter des sources (manuel + deep research) | Matrice ACH formelle |
| Détecter des signaux faibles | Mise à jour bayésienne formelle |
| Générer des hypothèses concurrentes brutes | Calibration agrégée (Brier, Murphy) |
| Évaluer la crédibilité des sources (1-5) | Graphe de connaissances consolidé |
| Scoring intuitif *a priori* | Synthèse narrative finale |
| Produire un rapport `.md` standardisé | |

Principe directeur : **chaque assertion porte son URL et un score de fiabilité** ;
aucune source n'est inventée ; les probabilités sont bornées à [0.05, 0.95] ; rien
n'est analysé sans **validation humaine** explicite.

---

## Pipeline

```
                 QUESTION D'INTELLIGENCE
                          │
        ┌─────────────────▼─────────────────┐
        │            OSINT-INTEL             │
        │                                    │
        │  0. Deep Research (multi-moteurs)  │  collecte sourcée
        │  ─ Barrière de validation humaine ─│  ← rien ne passe sans vous
        │  1. Structuration                  │
        │  2. Analyse terrain                │  hypothèses · scénarios · risques
        │  3. Export                         │
        │                                    │
        │   → rapport-osint.md (YAML)        │
        └─────────────────┬─────────────────┘
                          │
            ┌─────────────┴─────────────┐
            ▼                           ▼
      IRIS-STATION                  YGGDRASIL
   (ACH, Bayes, calib.)        (arbre, bifurcations)
```

**Mode descendant (reverse)** : OSINT-Intel peut aussi reprendre un rapport
IRIS-Station / Yggdrasil pour le re-challenger sous l'angle renseignement
(signaux ignorés, acteurs absents, scores confrontés à de nouvelles sources).

---

## Installation et lancement

Aucune compilation. Le logiciel s'utilise via une **interface web locale**.

1. Installez **Python 3.12** ([python.org](https://www.python.org)) — sous Windows,
   cochez « Add Python to PATH ».
2. Double-cliquez sur le lanceur de votre système, à la racine du dossier :
   - **Windows** : `lancer-windows.bat`
   - **macOS** : `lancer-macos.command` *(au 1ᵉʳ lancement : clic droit → Ouvrir)*
   - **Linux** : `lancer-linux.sh`
3. Le lanceur installe les dépendances (`requirements.txt`) puis ouvre votre
   navigateur sur `http://127.0.0.1:8765`.

> **Important** : après toute modification d'un fichier de code, il faut **arrêter
> puis relancer** l'application (fermer la fenêtre / Ctrl+C, puis relancer) pour que
> les changements soient pris en compte. Remplacer un fichier ne suffit pas si le
> serveur tourne déjà.

Lancement manuel équivalent :

```bash
pip install -r requirements.txt
python modules/osint-intel/app.py        # → http://127.0.0.1:8765
```

Dépendances (`requirements.txt`) : `pyyaml`, `ddgs`, `tavily-python`, `exa-py`.

---

## Configuration (clés API)

Tout se règle dans le panneau **« ⚙ Configuration »** de l'interface. Les clés sont
masquées et stockées localement (jamais affichées en clair).

| Service | Rôle | Clé | Où l'obtenir |
|---|---|---|---|
| **FantasyAI** | LLM cloud (analyse + synthèse) | requise pour l'analyse | clé fournie par FantasyAI |
| **Ollama** | LLM local (alternative) | aucune (local) | `ollama pull <modèle>` |
| **Tavily** | moteur de recherche principal | optionnelle (sans clé = mode bridé) | [tavily.com](https://tavily.com) — 1000/mois, sans carte |
| **Exa** | moteur sémantique additif | **requise** (sinon ignoré) | [exa.ai](https://exa.ai) — 1000/mois + 10 $, sans carte |

- La clé FantasyAI (et le modèle) se gère dans le panneau ; elle est stockée dans
  `modules/osint-intel/llm.json`.
- Les clés Tavily et Exa sont stockées dans
  `modules/osint-intel/deep-research/sources.json`.
- L'**analyse** (hypothèses, scénarios) nécessite un LLM (FantasyAI ou Ollama). La
  **synthèse extractive** du corpus, elle, fonctionne sans LLM.

---

## Moteurs de recherche

Architecture en deux régimes : les **généralistes** forment une chaîne de repli par
priorité (le premier qui répond coupe les suivants) ; les sources **additives** et
**spécialisées** sont toujours ajoutées.

| Moteur | Type | Rôle | Clé | Notes |
|---|---|---|---|---|
| **Tavily** | API IA | **primaire** (web + actualité datée) | optionnelle | contenu propre, conçu pour le RAG |
| **Exa** | API IA | **additif** (factuel/contradictoire/signaux faibles) | requise | recherche sémantique ; pas l'actualité |
| **DuckDuckGo** | web | repli généraliste | non | via `ddgs` |
| **News (ddgs)** | actualité | repli actualité (horizon ≤ 12 mois) | non | via `ddgs` |
| **Wikipedia** | encyclopédie | contexte (spécialisé) | non | bibliothèque standard |
| **Wayback** | archives | enrichissement (snapshot par URL) | non | bibliothèque standard |
| **ArXiv** | académique | désactivé par défaut | non | réactivable au besoin |

**Moteurs écartés** (et pourquoi) : `GDELT` et `SearXNG` (rate-limit / auto-hébergement),
puis `Qwant` et `GNews` (blocage anti-bot : 403 Cloudflare, refus silencieux de Google).
Leçon retenue : seules les **vraies API à clé** (Tavily, Exa) tiennent dans la durée ;
le scraping de moteurs non documentés finit toujours par être bloqué. Le code de ces
backends reste en sommeil dans `search.py` (réversible), mais ils ne sont pas activés.

Un **filtre de pertinence par entités** écarte après collecte les résultats qui ne
mentionnent pas les entités propres de la question (pays — avec gentilés et capitales —
et autres noms propres), avec un garde-fou qui ne vide jamais entièrement les résultats.
Activable/désactivable via la case « filtrer hors-sujet ».

---

## Utilisation

1. **Question** : saisissez la question d'intelligence ; réglez la **fraîcheur**
   (jour / semaine / mois / année), la synthèse (extractive ou LLM) et l'analyse.
2. **Recherche** : lancez la collecte. Le compteur « Par moteur » indique l'origine
   des résultats et le nombre d'articles hors-sujet écartés.
3. **Sources** : dans le panneau « 🗂 Sources actives », activez/désactivez les moteurs.
4. **Validation** : passez en revue le corpus, conservez/rejetez chaque source, ajoutez
   des sources manuelles, puis lancez l'analyse. **Rien n'est analysé sans validation.**
5. **Analyse → Export** : le rapport `rapport-osint.md` est produit avec son bloc YAML
   d'en-tête, prêt à être importé par IRIS-Station ou Yggdrasil.
6. **Mode descendant** : onglet dédié pour reprendre et re-challenger un rapport
   IRIS-Station / Yggdrasil.

---

## Format d'échange (contrat d'interface)

Tous les modules communiquent via un fichier `.md` doté d'un bloc **YAML front matter**.
C'est le contrat d'interface de l'écosystème : OSINT-Intel le **produit**, IRIS-Station
et Yggdrasil le **consomment** (et inversement en mode descendant).

Le validateur `shared/exchange_format.py` vérifie le schéma (champs obligatoires,
bornes de probabilité, rejet d'un YAML malformé). Voir des exemples conformes et
volontairement cassés dans `tests/`.

---

## Arborescence

```
IRIS-Standalone/
├── README.md                        ← ce fichier
├── requirements.txt                 ← dépendances Python (pyyaml, ddgs, tavily-python, exa-py)
├── lancer-windows.bat               ← lanceurs « double-clic » (installent + démarrent l'app)
├── lancer-macos.command
├── lancer-linux.sh
│
├── modules/
│   └── osint-intel/                 ← LE module (branche terrain)
│       ├── app.py                   ← serveur GUI local (port 8765, ouvre le navigateur)
│       ├── interface.html           ← interface unique (onglets Analyse + Mode descendant)
│       ├── llm.json                 ← config LLM (FantasyAI / Ollama)
│       ├── analyse.py               ← analyse terrain (Bayes simple, Brier unitaire)
│       ├── export.py                ← génération du rapport + bloc YAML
│       ├── mode_descendant.py       ← flux inverse (reprise d'un rapport IRIS/Yggdrasil)
│       ├── run_analyse.py           ← lancement CLI de l'analyse
│       ├── run_descendant.py        ← lancement CLI du mode descendant
│       ├── references/              ← (réservé, .gitkeep)
│       │
│       ├── deep-research/           ← moteur de collecte (étape 0)
│       │   ├── search.py            ← backends + chaîne de repli + filtre de pertinence
│       │   ├── sources.json         ← config des moteurs (priorités, clés, conditions)
│       │   ├── scoring.json         ← grille de crédibilité + corroboration
│       │   ├── synthesizer.py       ← synthèse du corpus (LLM ou extractive) + scoring
│       │   ├── llm_adapters.py      ← adaptateurs Ollama / FantasyAI
│       │   ├── fixtures.py          ← jeux de test hors-réseau
│       │   └── run_deep_research.py ← lancement CLI de la collecte
│       │
│       └── validation/              ← barrière de validation humaine
│           ├── panneau.html         ← UI de validation des sources
│           ├── serveur_validation.py
│           ├── validation_gate.py
│           └── src-tauri/           ← scaffold Tauri (non utilisé — voir Limitations)
│
├── shared/                          ← code transverse à toutes les branches
│   ├── exchange_format.py           ← schéma + parseur + validateur du YAML d'échange
│   └── findings_cross/
│       └── findings-cross-projets.md← base de connaissances inter-projets
│
├── iris-launcher/                   ← page d'accueil des 3 branches
│   ├── index.html
│   ├── INTEGRATION.md
│   └── src-tauri/                   ← scaffold Tauri (non utilisé)
│
├── data/                            ← espace de travail utilisateur
│   ├── calibration-log.yaml
│   └── projets/                     ← un sous-dossier par projet (.gitkeep)
│
└── tests/                           ← exemples de fichiers d'échange
    ├── exemple-conforme.md          ← YAML valide (doit passer)
    ├── exemple-casse.md             ← YAML invalide (doit être rejeté)
    ├── exemple-yaml-malforme.md
    ├── exemple-corpus.md
    ├── exemple-corpus-valide.md
    ├── exemple-rapport-osint.md
    ├── exemple-rapport-rechallenge.md
    └── exemple-entree-iris.md       ← exemple d'entrée en mode descendant
```

---

## Limitations connues

- **Précision de la captation d'actualité** : même avec plusieurs moteurs et l'élagage
  par l'IA, la pertinence des résultats d'**actualité** reste perfectible. Le filtre par
  entités réduit le hors-sujet, mais le classement fin des nouvelles est encore un
  chantier ouvert — c'est la principale piste d'amélioration du module.
- **Services externes non testables hors-ligne** : Tavily, Exa, DuckDuckGo et les LLM
  nécessitent une connexion ; ils ne peuvent être validés qu'à l'usage réel.
- **Clés requises** : Exa ne fonctionne pas sans clé ; Tavily fonctionne sans clé mais
  bridé. Les offres gratuites sont plafonnées (~1000 requêtes/mois).
- **Analyse = LLM** : la production d'hypothèses et de scénarios exige un LLM (FantasyAI
  ou Ollama) ; seule la synthèse extractive s'en passe.
- **Scaffold Tauri non utilisé** : les dossiers `src-tauri/` sont présents mais ni
  utilisés ni testés. L'usage recommandé et supporté est l'**interface web locale**.

---

## Écosystème IRIS∞

| Branche | Rôle | Statut |
|---|---|---|
| **OSINT-Intel** | Terrain : collecte, tri, hypothèses brutes | ce dépôt |
| **IRIS-Station** | Laboratoire : ACH, Bayes, calibration, graphe | branche sœur |
| **Yggdrasil** | Exploration : arbre des possibles, bifurcations | branche sœur |

Chaque branche est **indépendante** ; elles ne communiquent que par le format d'échange
(`.md` + YAML) et la base `findings-cross-projets.md`.

---

## État du projet

Les cinq phases de réalisation sont livrées : (1) socle + contrat d'interface,
(2) moteur Deep Research, (3) barrière de validation humaine, (4) pipeline d'analyse
terrain + export YAML, (5) mode descendant + intégration launcher.

---

## Licence

À définir par l'auteur avant publication (par ex. MIT, Apache-2.0 ou AGPL-3.0).
Ajoutez un fichier `LICENSE` à la racine.

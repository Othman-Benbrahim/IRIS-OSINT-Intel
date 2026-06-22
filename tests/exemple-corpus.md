---
corpus:
  version: '1.0'
  question: Quelle est la probabilité d'une crise financière dans les marchés émergents
    en 2027 ?
  horodatage: '2026-06-20T21:09:47+00:00'
  mode_collecte: fixtures
  mode_synthese: extractif
  hors_ligne: false
  backends_actifs:
  - fixtures
  parse:
    question: Quelle est la probabilité d'une crise financière dans les marchés émergents
      en 2027 ?
    entites:
    - Quelle
    termes_cles:
    - d'une
    - crise
    - financière
    - marchés
    - émergents
    - '2027'
    horizon_mois: 18
    domaine_academique: false
  requetes:
  - angle: factuel
    requete: d'une crise financière marchés émergents
  - angle: prospectif
    requete: d'une crise financière marchés émergents perspectives 2027
  - angle: contradictoire
    requete: d'une crise financière marchés émergents risques critiques arguments
      contre
  - angle: signaux_faibles
    requete: d'une crise financière marchés émergents signes avant-coureurs signaux
      faibles
  entites:
  - nom: Quelle
    type: à_qualifier
    occurrences: 2
  - nom: FMI
    type: à_qualifier
    occurrences: 1
  - nom: Reuters
    type: à_qualifier
    occurrences: 1
  - nom: EMBI
    type: à_qualifier
    occurrences: 1
  - nom: Perspectives
    type: à_qualifier
    occurrences: 1
  - nom: Banque
    type: à_qualifier
    occurrences: 1
  - nom: Pourquoi
    type: à_qualifier
    occurrences: 1
  - nom: Hausse
    type: à_qualifier
    occurrences: 1
  - nom: Chine
    type: à_qualifier
    occurrences: 1
  relations: []
  chronologie:
  - date: '2026-04-12'
    evenement: 'FMI : la dette des marchés émergents atteint un record en 2026'
    url: https://www.imf.org/fr/news/articles/2026/dette-emergents
  - date: '2026-04-28'
    evenement: Hausse discrète des lignes de swap entre la Chine et les émergents
    url: https://www.ft.com/content/swaps-chine-emergents-2026
  - date: '2026-05-03'
    evenement: 'Reuters : les spreads EMBI se tendent sur fond d''incertitude'
    url: https://www.reuters.com/markets/embi-spreads-2026
  - date: '2026-05-20'
    evenement: Pourquoi une crise généralisée reste peu probable
    url: https://www.economist.com/finance/2026/emergents-resilience
  - date: '2026-06-01'
    evenement: 'Perspectives 2027 : la Banque mondiale anticipe un ralentissement'
    url: https://www.worldbank.org/fr/perspectives-2027
  assertions:
  - texte: Le FMI rapporte que l'endettement public des marchés émergents a atteint
      un niveau record au premier trimestre 2026.
    url: https://www.imf.org/fr/news/articles/2026/dette-emergents
    fiabilite: 5
    backend: fixtures
  - texte: Les spreads de l'indice EMBI Global se sont écartés de 80 points de base
      depuis janvier, selon JPMorgan, signe d'une nervosité croissante des investisseurs.
    url: https://www.reuters.com/markets/embi-spreads-2026
    fiabilite: 4
    backend: fixtures
  - texte: La Banque mondiale anticipe un ralentissement de la croissance des émergents
      en 2027, sans toutefois prévoir de crise systémique généralisée dans son scénario
      central.
    url: https://www.worldbank.org/fr/perspectives-2027
    fiabilite: 5
    backend: fixtures
  - texte: Plusieurs économistes soulignent que les réserves de change accumulées
      depuis 2020 rendent une crise en chaîne moins probable qu'en 1997 ou 2008.
    url: https://www.economist.com/finance/2026/emergents-resilience
    fiabilite: 4
    backend: fixtures
  - texte: Le volume des accords de swap de devises entre la Chine et plusieurs banques
      centrales émergentes a doublé par rapport à 2025, un mouvement peu commenté
      publiquement.
    url: https://www.ft.com/content/swaps-chine-emergents-2026
    fiabilite: 4
    backend: fixtures
  signaux_faibles: []
  fiabilite_globale: 4.4
  lacunes:
  - Signaux faibles non détectés en mode extractif — brancher un LLM (synthetiser(...,
    llm=...)) pour cette étape.
  inaccessibles: []
---

# Corpus Deep Research — Quelle est la probabilité d'une crise financière dans les marchés émergents en 2027 ?

_Collecte fixtures · synthèse extractif · fiabilité globale 4.4/5 · 5 assertion(s)_

## Assertions sourcées
- [5/5] Le FMI rapporte que l'endettement public des marchés émergents a atteint un niveau record au premier trimestre 2026. — https://www.imf.org/fr/news/articles/2026/dette-emergents  (fixtures)
- [4/5] Les spreads de l'indice EMBI Global se sont écartés de 80 points de base depuis janvier, selon JPMorgan, signe d'une nervosité croissante des investisseurs. — https://www.reuters.com/markets/embi-spreads-2026  (fixtures)
- [5/5] La Banque mondiale anticipe un ralentissement de la croissance des émergents en 2027, sans toutefois prévoir de crise systémique généralisée dans son scénario central. — https://www.worldbank.org/fr/perspectives-2027  (fixtures)
- [4/5] Plusieurs économistes soulignent que les réserves de change accumulées depuis 2020 rendent une crise en chaîne moins probable qu'en 1997 ou 2008. — https://www.economist.com/finance/2026/emergents-resilience  (fixtures)
- [4/5] Le volume des accords de swap de devises entre la Chine et plusieurs banques centrales émergentes a doublé par rapport à 2025, un mouvement peu commenté publiquement. — https://www.ft.com/content/swaps-chine-emergents-2026  (fixtures)

## Chronologie
- 2026-04-12 — FMI : la dette des marchés émergents atteint un record en 2026 (https://www.imf.org/fr/news/articles/2026/dette-emergents)
- 2026-04-28 — Hausse discrète des lignes de swap entre la Chine et les émergents (https://www.ft.com/content/swaps-chine-emergents-2026)
- 2026-05-03 — Reuters : les spreads EMBI se tendent sur fond d'incertitude (https://www.reuters.com/markets/embi-spreads-2026)
- 2026-05-20 — Pourquoi une crise généralisée reste peu probable (https://www.economist.com/finance/2026/emergents-resilience)
- 2026-06-01 — Perspectives 2027 : la Banque mondiale anticipe un ralentissement (https://www.worldbank.org/fr/perspectives-2027)

## Lacunes
- Signaux faibles non détectés en mode extractif — brancher un LLM (synthetiser(..., llm=...)) pour cette étape.

---
iris_exchange:
  version: '1.0'
  source: osint-intel
  source_version: '2.0'
  timestamp: '2026-06-21T09:24:01+00:00'
  session_id: OSINT-2026-06-21-092401
  question_intelligence: Quelle est la probabilité d'une crise financière dans les
    marchés émergents en 2027 ?
  mode: complet
  deep_research_used: true
  hypotheses:
  - name: Crise systémique par défaut souverain en chaîne
    probability_prior: 0.25
    type: dominante
    id: H1
  - name: Correction ordonnée avec intervention multilatérale
    probability_prior: 0.45
    type: dissidente
    id: H2
  - name: Évitement par croissance surprise des émergents
    probability_prior: 0.2
    type: fractale
    id: H3
  scenarios:
  - name: Crise aiguë généralisée
    probability: 0.15
    indicators:
    - Spread EMBI > 800bps
    - ≥2 défauts souverains
    id: S1
  - name: Correction ordonnée FMI
    probability: 0.55
    indicators:
    - Accord préventif FMI
    - Coordination G20
    id: S2
  - name: Stagflation sans crise
    probability: 0.3
    indicators:
    - Croissance mondiale < 2%
    id: S3
  predictions:
  - question: Spread EMBI Global < 600bps au 31/12/2026 ?
    probability: 0.65
    type: binaire
    horizon: '2026-12-31'
    indicators:
    - JPMorgan EMBI Global
    id: PRED-001
  - question: Au moins un défaut souverain déclaré en 2026 ?
    probability: 0.3
    type: binaire
    horizon: '2026-12-31'
    indicators:
    - Annonces S&P/Moody's
    id: PRED-002
  signaux_faibles:
  - signal: Doublement des swaps de devises Chine-émergents
    direction: ↑
    significance: haute
  sources:
    total: 5
    deep_research: 5
    manuelles: 0
    fiabilite_moyenne: 4.4
  entites_cles:
  - nom: FMI
    type: à_qualifier
  - nom: Reuters
    type: à_qualifier
  - nom: EMBI
    type: à_qualifier
  - nom: Perspectives
    type: à_qualifier
  - nom: Banque
    type: à_qualifier
  - nom: Pourquoi
    type: à_qualifier
  - nom: Hausse
    type: à_qualifier
  - nom: Chine
    type: à_qualifier
  biais_detectes:
  - biais: Ancrage sur la crise de 2008
    correction: Élargir le base rate à 1990-2026
  lacunes:
  - Réserves de change par pays (Q2 2026) non couvertes
  - Signaux faibles non détectés en mode extractif — brancher un LLM (synthetiser(...,
    llm=...)) pour cette étape.
  signaux_a_surveiller:
  - Lignes de swap Fed
  - Dégradation S&P d'un poids lourd émergent
  pour_iris_station:
    hypotheses_a_formaliser:
    - H1
    - H2
    - H3
    predictions_a_scorer:
    - PRED-001
    - PRED-002
    calibration_attendue: Formalisation ACH + calibration agrégée → IRIS-Station
---

# Rapport OSINT-Intel — Quelle est la probabilité d'une crise financière dans les marchés émergents en 2027 ?

_Session OSINT-2026-06-21-092401 · mode complet · 5 source(s) · fiabilité 4.4/5_

## Hypothèses concurrentes (priors intuitifs — niveau terrain)
- **H1** (dominante, prior 0.25) — Crise systémique par défaut souverain en chaîne
- **H2** (dissidente, prior 0.45) — Correction ordonnée avec intervention multilatérale
- **H3** (fractale, prior 0.2) — Évitement par croissance surprise des émergents

## Scénarios
- **S1** (p=0.15) — Crise aiguë généralisée  
  indicateurs : Spread EMBI > 800bps · ≥2 défauts souverains
- **S2** (p=0.55) — Correction ordonnée FMI  
  indicateurs : Accord préventif FMI · Coordination G20
- **S3** (p=0.3) — Stagflation sans crise  
  indicateurs : Croissance mondiale < 2%

## Prédictions brutes
- **PRED-001** (p=0.65, échéance 2026-12-31) — Spread EMBI Global < 600bps au 31/12/2026 ?
- **PRED-002** (p=0.3, échéance 2026-12-31) — Au moins un défaut souverain déclaré en 2026 ?

## Signaux faibles
- ↑ [haute] Doublement des swaps de devises Chine-émergents

## Évaluation du risque
Risque modéré et conditionnel : ordonné si coordination multilatérale, aigu en cas de défaut isolé non contenu.

## Recommandations
- Surveiller les communiqués FMI/G20
- Transmettre à IRIS-Station pour formalisation ACH

## Transmission → IRIS-Station
La formalisation (matrice ACH multi-hypothèses, Bayes logarithmique) et la calibration agrégée (Murphy, patterns sur N) relèvent d'IRIS-Station. Ce rapport fournit les hypothèses brutes et les prédictions à scorer.

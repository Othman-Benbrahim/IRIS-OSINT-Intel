---
iris_exchange:
  version: "1.0"
  source: "osint-intel"
  timestamp: "2026/06/19 01:31"          # timestamp NON ISO 8601 -> erreur
  # session_id ABSENT                     -> erreur (champ obligatoire)
  question_intelligence: "Question test cassée"
  mode: "ultra"                           # mode hors vocabulaire -> erreur
  deep_research_used: true

  hypotheses:                             # seulement 2 hypothèses -> erreur (>=3)
    - id: "H1"
      name: "Hypothèse à prior impossible"
      probability_prior: 1.0              # hors bornes [0.05, 0.95] -> erreur
      type: "principale"                  # type hors vocabulaire -> erreur
    - id: "H2"
      name: "Seconde hypothèse"
      probability_prior: 0.40
      type: "dissidente"

  scenarios:                              # somme = 0.70 -> erreur (doit ≈ 1.0)
    - id: "S1"
      name: "Scénario A"
      probability: 0.40
      indicators: ["ind1"]
    - id: "S2"
      name: "Scénario B"
      probability: 0.30
      indicators: ["ind2"]

  predictions:
    - id: "PRED-001"
      question: "Prédiction à probabilité nulle ?"
      probability: 0.0                    # hors bornes -> erreur
      type: "binaire"
      # horizon ABSENT                    -> erreur (champ obligatoire)

  sources:
    total: 10                             # 7 + 5 = 12 ≠ 10 -> avertissement
    deep_research: 7
    manuelles: 5
    fiabilite_moyenne: 3.8

  # pour_iris_station ABSENT              -> avertissement (recommandé)
---

# Rapport cassé (pour test du validateur)

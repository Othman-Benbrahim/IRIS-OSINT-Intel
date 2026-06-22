---
iris_exchange:
  version: '1.0'
  source: osint-intel
  source_version: '2.0'
  timestamp: '2026-06-22T10:13:28+00:00'
  session_id: OSINT-2026-06-22-101328
  question_intelligence: ''
  mode: complet
  deep_research_used: true
  hypotheses:
  - name: La canicule constitue le facteur dominant de perturbation intérieure immédiate
      en France, avec restrictions publiques, fermetures scolaires et reports d'examens.
    probability_prior: 0.75
    type: dominante
    id: H1
  - name: L'agenda politico-législatif national reste capable de progresser malgré
      la pression climatique, notamment sur le texte relatif à la fin de vie.
    probability_prior: 0.55
    type: dissidente
    id: H2
  - name: Les signaux défense, cloud, satellite et mission-critical indiquent une
      recomposition sectorielle discrète autour de souveraineté, connectivité résiliente
      et capacités de frappe longue portée.
    probability_prior: 0.45
    type: fractale
    id: H3
  scenarios:
  - name: Perturbation intérieure limitée mais visible par la canicule
    probability: 0.55
    indicators:
    - 49 départements et environ 35 millions de Français en vigilance rouge canicule
    - Restrictions de consommation d'alcool dans l'espace public et limitation d'activités
      sportives extérieures
    - Écoles fermées et oraux reportés signalés dans l'éducation
    - Records de chaleur attendus
    id: S1
  - name: Maintien de la continuité institutionnelle malgré les perturbations
    probability: 0.3
    indicators:
    - Nouvel examen à l'Assemblée du texte sur la fin de vie
    - Adoption définitive annoncée comme attendue le 15 juillet sauf coup de théâtre
    - Les mesures d'adaptation scolaires restent présentées comme des aménagements
      plutôt qu'un arrêt généralisé
    id: S2
  - name: Glissement de l'attention vers sécurité, souveraineté et recomposition politique
    probability: 0.15
    indicators:
    - Négociations exclusives de la France avec MBDA et Safran pour une frappe longue
      portée
    - Référence à une fourniture de lance-roquettes multiples par MBDA-Safran
    - Bardella affirme en Pologne vouloir gagner en 2027 et changer le cap de l'UE
    - Alibaba ouvre une région cloud en France et RugGear rejoint un dispositif mission-critical
      Vodafone
    id: S3
  predictions:
  - question: La vigilance rouge canicule restera-t-elle un sujet central d'actualité
      nationale en France dans les 72 prochaines heures ?
    probability: 0.7
    type: binaire
    horizon: '2026-06-25'
    indicators:
    - La canicule frappe le pays depuis près d'une semaine
    - 49 départements sont déjà en vigilance rouge
    - Des records de chaleur sont attendus
    - Des restrictions et fermetures sont déjà actées
    id: PRED-001
  - question: Le texte sur la fin de vie sera-t-il adopté définitivement à la date
      annoncée ?
    probability: 0.6
    type: binaire
    horizon: '2026-07-15'
    indicators:
    - Les députés réexaminent le texte pour la troisième fois
    - L'adoption à nouveau est décrite comme probable sauf coup de théâtre
    - L'adoption définitive est annoncée pour le 15 juillet
    id: PRED-002
  - question: Les perturbations scolaires liées à la canicule resteront-elles visibles
      à court terme ?
    probability: 0.65
    type: binaire
    horizon: '2026-06-25'
    indicators:
    - Oraux reportés
    - Écoles fermées
    - Éducation contrainte à des aménagements face à la canicule
    - Vigilance rouge dans 49 départements
    id: PRED-003
  - question: La thématique défense-souveraineté française continuera-t-elle à émerger
      dans les annonces publiques dans le mois à venir ?
    probability: 0.5
    type: binaire
    horizon: '2026-07-22'
    indicators:
    - Négociations exclusives avec MBDA et Safran pour frappe longue portée
    - Sélection du tandem MBDA-Safran pour lance-roquettes multiples
    - Présence simultanée de signaux cloud, satellite et mission-critical
    id: PRED-004
  signaux_faibles:
  - signal: Accumulation d'articles sur la canicule avec restrictions, écoles fermées,
      examens reportés et vigilance rouge massive.
    direction: ↑
    significance: haute
  - signal: Mention d'une adoption quasi attendue du texte sur la fin de vie malgré
      le contexte de perturbation nationale.
    direction: →
    significance: moyenne
  - signal: Convergence MBDA-Safran sur frappe longue portée et lance-roquettes multiples.
    direction: ↗
    significance: moyenne
  - signal: 'Présence d''acteurs de connectivité et cloud en France ou autour de services
      critiques : Starlink/Kyivstar, Vodafone/RugGear, Alibaba cloud region.'
    direction: ↗
    significance: basse
  - signal: Projection politique de Bardella vers 2027 et inflexion européenne depuis
      la Pologne.
    direction: ↗
    significance: basse
  sources:
    total: 11
    deep_research: 11
    manuelles: 0
    fiabilite_moyenne: 2.0
  entites_cles:
  - nom: France
    type: à_qualifier
  - nom: Actualités
    type: à_qualifier
  - nom: Monde
    type: à_qualifier
  - nom: Infos
    type: à_qualifier
  - nom: Eurobites
    type: à_qualifier
  - nom: Kyvistar
    type: à_qualifier
  - nom: Starlink
    type: à_qualifier
  - nom: Light Reading
    type: à_qualifier
  biais_detectes:
  - biais: Surpondération médiatique de la canicule car plusieurs assertions proviennent
      d'articles redondants sur le même événement.
    correction: Traiter la canicule comme dominante à court terme, mais isoler les
      autres lignes défense, politique et technologies comme signaux distincts non
      confirmés par volume équivalent.
  - biais: Risque de confusion temporelle et thématique dû à des titres ou URL non
      alignés, notamment Euronews et Defense News.
    correction: Limiter l'analyse aux formulations explicites des assertions et éviter
      d'inférer au-delà des extraits fournis.
  - biais: Fiabilité uniforme faible à moyenne indiquée à 2 pour toutes les sources.
    correction: Maintenir des probabilités prudentes et ne pas convertir les signaux
      en certitudes opérationnelles.
  lacunes:
  - La question analytique n'est pas explicitement formulée.
  - Absence de données chiffrées sur mortalité, saturation hospitalière, réseau électrique
    ou transports pendant la canicule.
  - Pas de détail sur les décisions préfectorales exactes ni leur durée.
  - Pas de calendrier précis pour les négociations MBDA-Safran ni de périmètre contractuel
    confirmé.
  - Pas de contenu détaillé sur l'accord Etats-Unis-Iran au-delà de la réouverture
    du détroit d'Ormuz et de l'annonce de fin des hostilités.
  - Pas d'éléments sur réactions sociales, syndicales ou opposition parlementaire
    au texte sur la fin de vie.
  - Signaux faibles non détectés en mode extractif — brancher un LLM (synthetiser(...,
    llm=...)) pour cette étape.
  signaux_a_surveiller:
  - Extension ou levée de la vigilance rouge canicule par Météo France.
  - Nouvelles fermetures d'écoles, reports d'examens ou restrictions d'activités extérieures.
  - Signalements de tensions sanitaires, énergétiques ou de transport liés à la chaleur.
  - Amendements, blocages ou confirmation du calendrier du texte sur la fin de vie
    avant le 15 juillet.
  - Communications officielles du ministère des Armées sur MBDA, Safran, frappe longue
    portée ou lance-roquettes multiples.
  - Clarifications sur l'accord Etats-Unis-Iran et effets sur le détroit d'Ormuz.
  - Positionnements politiques français reliant crise climatique, gestion publique
    et échéance 2027.
  pour_iris_station:
    hypotheses_a_formaliser:
    - H1
    - H2
    - H3
    predictions_a_scorer:
    - PRED-001
    - PRED-002
    - PRED-003
    - PRED-004
    calibration_attendue: Formalisation ACH + calibration agrégée → IRIS-Station
---

# Rapport OSINT-Intel — 

_Session OSINT-2026-06-22-101328 · mode complet · 11 source(s) · fiabilité 2.0/5_

## Hypothèses concurrentes (priors intuitifs — niveau terrain)
- **H1** (dominante, prior 0.75) — La canicule constitue le facteur dominant de perturbation intérieure immédiate en France, avec restrictions publiques, fermetures scolaires et reports d'examens.
- **H2** (dissidente, prior 0.55) — L'agenda politico-législatif national reste capable de progresser malgré la pression climatique, notamment sur le texte relatif à la fin de vie.
- **H3** (fractale, prior 0.45) — Les signaux défense, cloud, satellite et mission-critical indiquent une recomposition sectorielle discrète autour de souveraineté, connectivité résiliente et capacités de frappe longue portée.

## Scénarios
- **S1** (p=0.55) — Perturbation intérieure limitée mais visible par la canicule  
  indicateurs : 49 départements et environ 35 millions de Français en vigilance rouge canicule · Restrictions de consommation d'alcool dans l'espace public et limitation d'activités sportives extérieures · Écoles fermées et oraux reportés signalés dans l'éducation · Records de chaleur attendus
- **S2** (p=0.3) — Maintien de la continuité institutionnelle malgré les perturbations  
  indicateurs : Nouvel examen à l'Assemblée du texte sur la fin de vie · Adoption définitive annoncée comme attendue le 15 juillet sauf coup de théâtre · Les mesures d'adaptation scolaires restent présentées comme des aménagements plutôt qu'un arrêt généralisé
- **S3** (p=0.15) — Glissement de l'attention vers sécurité, souveraineté et recomposition politique  
  indicateurs : Négociations exclusives de la France avec MBDA et Safran pour une frappe longue portée · Référence à une fourniture de lance-roquettes multiples par MBDA-Safran · Bardella affirme en Pologne vouloir gagner en 2027 et changer le cap de l'UE · Alibaba ouvre une région cloud en France et RugGear rejoint un dispositif mission-critical Vodafone

## Prédictions brutes
- **PRED-001** (p=0.7, échéance 2026-06-25) — La vigilance rouge canicule restera-t-elle un sujet central d'actualité nationale en France dans les 72 prochaines heures ?
- **PRED-002** (p=0.6, échéance 2026-07-15) — Le texte sur la fin de vie sera-t-il adopté définitivement à la date annoncée ?
- **PRED-003** (p=0.65, échéance 2026-06-25) — Les perturbations scolaires liées à la canicule resteront-elles visibles à court terme ?
- **PRED-004** (p=0.5, échéance 2026-07-22) — La thématique défense-souveraineté française continuera-t-elle à émerger dans les annonces publiques dans le mois à venir ?

## Signaux faibles
- ↑ [haute] Accumulation d'articles sur la canicule avec restrictions, écoles fermées, examens reportés et vigilance rouge massive.
- → [moyenne] Mention d'une adoption quasi attendue du texte sur la fin de vie malgré le contexte de perturbation nationale.
- ↗ [moyenne] Convergence MBDA-Safran sur frappe longue portée et lance-roquettes multiples.
- ↗ [basse] Présence d'acteurs de connectivité et cloud en France ou autour de services critiques : Starlink/Kyivstar, Vodafone/RugGear, Alibaba cloud region.
- ↗ [basse] Projection politique de Bardella vers 2027 et inflexion européenne depuis la Pologne.

## Évaluation du risque
Le risque principal à court terme est une perturbation intérieure française amplifiée par la canicule, avec effets administratifs, scolaires et sanitaires possibles, tandis que des dossiers politiques et défense avancent en arrière-plan.

## Recommandations
- Prioriser la veille terrain sur départements en vigilance rouge, fermetures scolaires, reports d'examens et restrictions locales.
- Distinguer les impacts confirmés de la canicule des extrapolations non sourcées sur crise sanitaire ou infrastructures.
- Maintenir une veille séparée sur le texte fin de vie jusqu'à l'échéance du 15 juillet.
- Suivre les annonces officielles Défense concernant MBDA-Safran sans conclure prématurément sur les capacités livrées.
- Surveiller les signaux politiques liés à 2027 uniquement comme arrière-plan stratégique, faute de données supplémentaires dans les assertions.

## Transmission → IRIS-Station
La formalisation (matrice ACH multi-hypothèses, Bayes logarithmique) et la calibration agrégée (Murphy, patterns sur N) relèvent d'IRIS-Station. Ce rapport fournit les hypothèses brutes et les prédictions à scorer.

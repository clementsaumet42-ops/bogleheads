# 🏦 Boglehead FR — Outil CGP Multi-Enveloppes 2026

> **Outil pédagogique** pour conseillers en gestion de patrimoine (CGP/CIF) et investisseurs autonomes.
> Génère un fichier Excel complet pour la gestion de portefeuille Boglehead multi-enveloppes fiscales.

> ⚠️ **Avertissement légal** : Cet outil est fourni à titre pédagogique uniquement. Il ne constitue pas un conseil en investissement personnalisé au sens de la Directive MIF II. Tout conseil patrimonial doit être personnalisé par un CIF/CGP agréé AMF. Les paramètres fiscaux 2026 sont indicatifs — valider avec votre expert-comptable.

---

## 📋 Description

Ce projet génère un fichier Excel **`output/portefeuille_bogleheads.xlsx`** contenant 17 onglets dédiés à la gestion d'un portefeuille Boglehead en France, avec optimisation multi-enveloppes fiscales (PEA, PER, PEE, CTO, Contrat Cap IS).

### Fonctionnalités

- 📊 **70 ETF** couvrant toutes les classes d'actifs (actions, obligations, or, REITs, matières premières)
- 🏦 **6 enveloppes fiscales** avec règles 2026 (PS 18,6%, PFU 31,4%, IS 15/25%)
- 👥 **6 profils clients types** (Cadre sup, Dirigeant grand groupe, Dirigeant PME, Profession libérale, Jeune cadre, Pré-retraité)
- 🧮 **Tutoriel Solveur Excel** pour l'optimisation d'asset location
- ⚖️ **Outil de rebalancement** avec bandes de tolérance (méthode Larry Swedroe)
- 💡 **Calculs fiscaux** : CEHR, CDHR, contrat capitalisation IS, mark-to-market
- 📈 **Projection Monte-Carlo** : simulation de 10 000 trajectoires sur 10/20/30 ans avec probabilité d'atteinte d'objectif
- 🔄 **Glide path automatique** (lifecycle investing) : évolution de l'allocation selon l'âge avec 6 stratégies paramétrables (Bogle, target-date, conservateur…)
- 💸 **Rebalancement par flux** (cash flow rebalancing) : rééquilibrage sans vente, zéro fiscalité
- 🎯 **Rebalancement optimal** (MILP + cascade fiscale) : plan d'action chiffré minimisant le coût fiscal, avec gestion CMP/FIFO, tax-loss harvesting, abattements AV, contraintes PEA/PER

---

## 🚀 Installation

### Prérequis

- Python 3.9+
- pip

### Installation des dépendances

```bash
pip install -r requirements.txt
```

---

## 📊 Utilisation

### Générer le fichier Excel

```bash
python build_excel.py
```

Le fichier est généré dans `output/portefeuille_bogleheads.xlsx`.

### Lancer les tests

```bash
pytest tests/ -v
```

---

## 📁 Structure du projet

```
bogleheads/
├── README.md
├── requirements.txt
├── .gitignore
├── build_excel.py              ← Point d'entrée
├── config/
│   ├── fiscalite_2026.yaml     ← Paramètres fiscaux France 2026
│   ├── enveloppes.yaml         ← Règles des 6 enveloppes fiscales
│   ├── univers_etf.yaml        ← 70 ETF Boglehead (schéma enrichi)
│   ├── profils_clients.yaml   ← 6 profils clients fictifs
│   ├── projection_params.yaml ← Hypothèses de rendement/volatilité
│   ├── glide_paths.yaml        ← Règles de glide paths
│   └── rebalancement_flux.yaml ← Bandes + fiscalité par enveloppe
├── src/
│   ├── fiscalite.py            ← Calculs PFU, IS, PEA, PER, CEHR, CDHR
│   ├── enveloppes.py           ← Règles métier enveloppes
│   ├── allocation.py           ← Allocation cible Boglehead
│   ├── asset_location.py       ← Optimisation asset location
│   ├── rebalancement.py        ← Rebalancement et coûts fiscaux
│   ├── rebalancement_flux.py   ← Rebalancement par flux (cash flow rebalancing)
│   ├── projection.py           ← Projection Monte-Carlo
│   ├── glide_path.py           ← Glide path (lifecycle investing)
│   └── excel_builder.py        ← Générateur Excel (openpyxl)
├── docs/
│   ├── regles_fiscales.md      ← Règles fiscales par enveloppe + articles CGI
│   ├── architecture.md         ← Architecture du projet
│   ├── tuto_solveur.md         ← Tutoriel Solveur Excel complet
│   └── schema_univers_etf.md   ← Schéma et documentation de univers_etf.yaml
├── tests/
│   ├── test_fiscalite.py       ← Tests calculs fiscaux
│   ├── test_profils.py         ← Tests profils clients
│   └── test_univers_etf.py     ← Tests validation univers ETF (ISIN, PEA, schéma)
└── output/
    └── .gitkeep
```

---

## 🎯 Rebalancement Optimal (S3.6)

Module `src/rebalancement_optimal.py` — Plan d'action chiffré en 3 étapes fiscales.

### Cascade de priorités

```
Étape 1 — GRATUIT (priorité absolue)
  ├─ Arbitrage intra-enveloppe PEA  (zéro fiscalité)
  ├─ Arbitrage intra-enveloppe PER  (zéro fiscalité)
  ├─ Arbitrage intra-enveloppe AV   (zéro fiscalité hors abattement)
  └─ Arbitrage intra-enveloppe Contrat Cap IS

Étape 2 — FLUX (dilue la dérive sans vendre)
  └─ Orienter versements vers classes sous-pondérées (rebalancement_flux.py)

Étape 3 — VENTE SI NÉCESSAIRE (optimisée fiscalement)
  ├─ 3a. AV > 8 ans  : abattement annuel 4 600 € / 9 200 €  (Art. 125-0 A CGI)
  ├─ 3b. PEA ≥ 5 ans : PS 17,2 % uniquement                 (Art. 150-0 A CGI)
  ├─ 3c. CTO/IR      : méthode CMP obligatoire               (BOI-RPPM-PVBMI-20-10-20-40)
  ├─ 3d. CTO/IS      : méthode FIFO + tax-loss harvesting    (PCG + art. 38 CGI)
  └─ 3e. PER         : sortie interdite sauf cas limitatifs  (Art. L. 224-4 CMF)
```

### Solveur MILP (PuLP)

Minimise `Σ coût_fiscal(vente) + Σ frais_courtage + pénalité_dérive_résiduelle`
sous contraintes d'allocation ±5 pp par classe et de blocage légal (PEA < 5 ans, PER).

```bash
# Activer l'extra optim pour PuLP
pip install -e ".[optim]"
```

### Paramétrage par profil (`config/profils_clients.yaml`)

```yaml
profil_1_cadre:
  regime_fiscal_detenteur: "IR"   # "IR" (particulier) ou "IS" (personne morale)
  positions_detaillees:
    - etf: "CW8"
      enveloppe: "PEA"
      quantite: 450
      prix_revient_moyen: 380.50      # CMP utilisé pour CTO/IR
      lots:                            # FIFO (CTO/IS) + traçabilité
        - date_acquisition: "2019-03-15"
          quantite: 200
          prix_unitaire: 360.00
      montant_actuel: 207000
      date_ouverture_enveloppe: "2018-03-15"
  abattements_utilises:
    av_abattement_annuel_restant: 4600  # reset au 1er janvier
  frais_courtier_par_transaction: 0.0   # 0 € chez Bourse Direct / TR
```

### Onglet Excel `Plan_Rebalancement`

Généré automatiquement dans `output/portefeuille_bogleheads.xlsx` :

```
═══ PLAN DE REBALANCEMENT — GÉNÉRÉ LE 2026-04-23 ═══
Dérive constatée :
  actions    : +8,2 pp  🔴   RÉDUIRE (surpondéré)
  obligations: −5,4 pp  🔴   AUGMENTER (sous-pondéré)

ÉTAPE 1 — ARBITRAGES GRATUITS (0 €)
  ✅ PEA : Vendre 15 000 € CSP1 → Acheter 15 000 € CW8   Coût : 0 €

ÉTAPE 2 — FLUX ENTRANTS (0 €)
  ➡️ Orienter 9 000 € vers obligations (sur 3 mois)       Coût : 0 €

ÉTAPE 3 — VENTES OPTIMISÉES
  ⚠️ CTO_perso : Vendre 14 000 € IWDA (méthode CMP)
     PV réalisée : 1 830 €   Coût fiscal : 0 € (TLH)  ✅

═══ RÉSULTATS ═══
  Coût fiscal total optimisé        :     0 €
  Coût fiscal sans optimisation     : 4 280 €
  ⭐ Économie fiscale               : 4 280 €
```

---

Le référentiel ETF est défini dans `config/univers_etf.yaml`. Il contient **70 ETF** couvrant toutes les classes d'actifs d'un portefeuille Boglehead.

### Classes d'actifs couvertes

| Classe | Nb ETF | Exemples |
|--------|--------|---------|
| Actions — Monde | 7 | CW8 (Amundi PEA), IWDA (iShares), VWCE (Vanguard), XMWO (Xtrackers) |
| Actions — USA | 5 | CSP1 (iShares), LYPS (Amundi/Lyxor PEA) |
| Actions — Europe | 3 | EXSA (iShares), C50 (Amundi EMU PEA) |
| Actions — Émergents | 5 | IEEM (iShares), PAEEM (Amundi PEA) |
| Actions — Facteurs | 4 | IWVL (Value), IWQU (Quality), IWMO (Momentum), MVOL (Min Vol) |
| Obligations | 12 | GOVS, AGGH, IEAA, IBTM, ITPS |
| Immobilier (REITs) | 3 | IWDP, EPRE, XREA |
| Or physique | 3 | GOLD, IGLN, XGLD |
| Matières premières | 2 | CMOD, LYTR |
| Monétaire | 2 | CSH, XEON |
| Thématiques / ESG | 7 | INRG, IHCG, WTAI, SUWU |

### Schéma enrichi

Chaque ETF dispose des champs suivants (nouveaux champs en **gras**) :

- `isin`, `ticker`, `nom`, `emetteur`, `classe_actifs`, `sous_classe`
- `ter`, `devise`, `domicile`, `capitalisant`, `eur_hedged`
- **`methode_replication`** : `physique` | `synthetique_swap` | `synthetique_swap_unfunded` | `physique_optimisee`
- **`url_dic_kid`** : URL du Document d'Informations Clés officiel (ou `null`)
- **`date_verification_dic`** : date ISO de dernière vérification
- `eligibilite` : `PEA`, `PER`, `PEE`, `CTO_perso`, `CTO_IS`, `Contrat_Cap_IS`, **`AV_UC`**
- **`contrats_av_reference`** : liste des contrats AV où l'ETF est disponible
- **`frais_entree_typique_pct`** : frais d'entrée typiques courtier

→ Voir **[docs/schema_univers_etf.md](docs/schema_univers_etf.md)** pour la documentation complète du schéma.

### Ajouter un ETF

1. Copier un bloc ETF existant dans `config/univers_etf.yaml`
2. Modifier `isin`, `nom`, `ticker`, et les autres champs
3. Sourcer le DIC/KID officiel → renseigner `url_dic_kid`
4. Vérifier l'éligibilité PEA (physique vs swap, domicile UE/EEE)
5. Lancer les tests de validation :

```bash
pytest tests/test_univers_etf.py -v
```

---



| Onglet | Description |
|---|---|
| `Paramètres_Client` | Saisie des paramètres du client |
| `Paramètres_Fiscalité_2026` | Référentiel fiscal France 2026 |
| `Enveloppes` | Tableau comparatif des 6 enveloppes |
| `Univers_ETF` | ~70 ETF avec éligibilité par enveloppe (tableau structuré) |
| `Allocation_Cible` | Allocation Boglehead par classe d'actifs |
| `Asset_Location_Matrice` | Matrice ETF × Enveloppe |
| `Rebalancement` | Outil de suivi des dérives d'allocation |
| `Reporting_Client` | Synthèse patrimoniale client |
| `Profils_Types` | Tableau des 6 profils types |
| `Profil_1_CADRE` | Cadre Supérieur Salarié (45 ans, TMI 41%) |
| `Profil_2_DIRIGEANT` | Cadre Dirigeant Grand Groupe (52 ans, TMI 45%, CEHR) |
| `Profil_3_DIRIGEANT` | Dirigeant PME avec Holding IS (50 ans, Contrat Cap IS) |
| `Profil_4_PROFESSION` | Profession Libérale / TNS (48 ans, PER Madelin) |
| `Profil_5_JEUNE` | Jeune Cadre en Constitution (32 ans, PEA priorité) |
| `Profil_6_PRE` | Pré-retraité / Cédant (62 ans, post-cession, glide path) |
| `Comparatif_Profils` | Gain fiscal estimé vs scénario naïf CTO |
| `Tuto_Solveur` | Tutoriel Solveur Excel pas-à-pas |
| `Projection_MonteCarlo` | Projection patrimoniale Monte-Carlo (10 000 tirages, percentiles 10/50/90) |
| `Glide_Path` | Trajectoire d'allocation dans le temps (lifecycle investing) |
| `Rebalancement_Flux` | Outil de rebalancement par flux avec comparaison fiscale |
| `Plan_Rebalancement` | Plan d'action chiffré (cascade fiscale 3 étapes : arbitrages gratuits → flux → ventes optimisées) |

---

## 👥 Profils clients

| # | Profil | Âge | TMI | Patrimoine fin. | Actions | Enveloppe clé |
|---|---|---|---|---|---|---|
| 1 | Cadre Supérieur Salarié | 45 ans | 41% | 500 000 € | 65% | PEA + PER + PEE |
| 2 | Cadre Dirigeant Grand Groupe | 52 ans | 45% | 1 500 000 € | 55% | PEA + PER + PEE (CEHR/CDHR) |
| 3 | Dirigeant PME avec Holding IS | 50 ans | 45% | 3 000 000 € | 55% | Contrat Cap IS + PEA |
| 4 | Profession Libérale / TNS | 48 ans | 45% | 1 000 000 € | 60% | PER Madelin + PEA |
| 5 | Jeune Cadre en Constitution | 32 ans | 30% | 150 000 € | 85% | PEA (priorité absolue) |
| 6 | Pré-retraité / Cédant | 62 ans | 45% | 5 000 000 € | 35% | Contrat Cap IS + glide path |

> Ces profils sont **entièrement fictifs** et construits à des fins pédagogiques.

---

## 🧮 Tutoriel Solveur Excel — Résumé

Le Solveur Excel permet d'optimiser la répartition des ETF entre les enveloppes pour **maximiser le capital net après impôts**.

### Formulation mathématique

```
MAX  Σ_i Σ_j VAN_ij(x_ij)
s.c. x_ij = 0  si ETF i non éligible à l'enveloppe j
     Σ_i x_i,PEA ≤ 150 000 - encours_PEA
     (α_k ± 5%) × P ≤ Σ_{classe k} x_ij ≤ (α_k + 5%) × P
     Σ_i Σ_j x_ij = P  (budget total)
     x_ij ≥ 0
```

### Activation du Solveur — Windows

1. `Fichier` → `Options` → `Compléments`
2. `Gérer : Compléments Excel` → `Atteindre`
3. Cocher ☑ `Solveur` → `OK`
4. `Données` → `Solveur`

### Activation du Solveur — Mac

1. `Excel` → `Préférences` → `Compléments`
2. Cocher ☑ `Solveur` → `OK`
3. Menu `Outils` → `Solveur`

### OpenSolver (recommandé pour 60 ETF × 6 enveloppes = 360 variables)

Le Solveur intégré est limité à 200 variables. Pour les portefeuilles complets, utiliser **OpenSolver** :
- Téléchargement gratuit : https://opensolver.org
- Supporte les MILP (décisions binaires d'ouverture d'enveloppe)
- Algorithmes CBC, GLPK, Gurobi

→ Voir `docs/tuto_solveur.md` pour le tutoriel complet avec exemple Profil 3.

---

## 📜 Règles fiscales clés 2026

| Enveloppe | Fiscalité sortie | Avantage vs CTO |
|---|---|---|
| **PEA (≥5 ans)** | 18,6% PS seulement | **−12,8% IR** |
| **PER** | TMI retraite + PS gains | Déduction à l'entrée |
| **PEE** | 18,6% PS seulement | **−12,8% IR** + abondement |
| **Contrat Cap IS** | IS 15/25% base forfaitaire | Pas de mark-to-market |
| CTO IS | IS 15/25% + **MTM annuel** | ⚠️ Piège MTM OPCVM |
| CTO perso | PFU 31,4% | Référence |

> **Prélèvements Sociaux 2026 : 18,6%** (CSG 12,1% + CRDS 0,5% + Solidarité 6,0%)
> **CEHR** : +3% (RFR 250-500k€) ou +4% (RFR > 500k€) — s'ajoute au PFU
> **CDHR** : taux effectif minimum 20% pour RFR > 250k€ — LF 2025

---

## 🏗️ Architecture

Voir `docs/architecture.md` pour le détail complet.

```
YAML configs ──→ src/*.py ──→ excel_builder.py ──→ output/*.xlsx
                    │
               tests/ pytest
```

---

## 🗺️ Roadmap & Fonctionnalités futures

> Liste des améliorations envisagées pour le projet, classées par thème et priorité.
> Les contributions sont les bienvenues — ouvrez une issue avant de commencer un gros chantier.

### 🔧 Qualité de code & outillage

- [ ] Découper `src/excel_builder.py` (71 Ko, monolithique) en sous-package `src/excel/` avec un fichier par onglet
- [ ] Ajouter le typage statique complet (`mypy`, type hints) sur tous les modules
- [ ] Valider les YAML avec **Pydantic v2** (modèles `ETF`, `Enveloppe`, `Profil`, `Fiscalite`)
- [ ] Migrer `requirements.txt` vers `pyproject.toml` (PEP 621) avec extras `[dev]`
- [ ] Ajouter `ruff` (lint + format), `.pre-commit-config.yaml`, `mypy` en strict
- [ ] Ajouter un fichier `LICENSE` explicite (MIT recommandé)
- [ ] Ajouter `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, templates d'issues et de PR

### 🤖 CI/CD

- [ ] Workflow GitHub Actions `ci.yml` : lint + tests + build Excel en artefact
- [ ] Matrice Python 3.9 / 3.10 / 3.11 / 3.12
- [ ] Couverture de tests `pytest --cov` + upload Codecov (objectif ≥ 80 %)
- [ ] Couvrir par des tests les modules `allocation.py`, `asset_location.py`, `rebalancement.py`, `enveloppes.py`, `excel_builder.py`
- [ ] Release GitHub automatique sur tag (build + asset `.xlsx` joint)

### 🎯 Fonctionnalités métier — Priorité haute

- [ ] **Optimiseur intégré** (`src/optimizer.py`) avec `pulp` ou `scipy.optimize.milp` — remplace le Solveur Excel et gère > 200 variables. L'Excel sort déjà optimisé.
- [x] **Projection patrimoniale Monte-Carlo** (`src/projection.py`) : 10 000 tirages, médiane + percentiles 10/90, probabilité d'atteindre un objectif, intégration des versements périodiques et de la fiscalité de sortie. Onglet Excel `Projection_30ans` avec graphiques.
- [x] **Glide path automatique** (lifecycle investing) : règles paramétrables dans `config/glide_paths.yaml` (Bogle 110-âge, target-date, conservateur), onglet `Glide_Path` par profil avec trajectoire année par année.

### 💡 Fonctionnalités métier — Priorité moyenne

- [ ] **Optimisation des versements** (DCA vs Lump-sum) : simulation des deux stratégies pour un apport ponctuel (prime de cession, héritage) + recommandation.
- [ ] **Tax-loss harvesting** (CTO) : détection des moins-values latentes en fin d'année pour compenser les plus-values.
- [ ] **Calculateur "sortie PER" optimale** : simulation rente / capital fractionné / capital en une fois selon TMI retraite.
- [x] **Rebalancement intelligent** :
  - [x] Rebalancement par flux (orienter les versements vers les classes sous-pondérées, pas de fiscalité)
  - [x] **Rebalancement optimal (MILP)** : `src/rebalancement_optimal.py` — cascade fiscale 3 étapes, CMP/FIFO, tax-loss harvesting, abattements AV, contraintes PEA/PER. Onglet Excel `Plan_Rebalancement`.
  - Onglet `Alertes` listant les positions à rebalancer
- [ ] **Optimisation Assurance-Vie avancée** :
  - Abattement annuel 4 600 € / 9 200 € après 8 ans
  - Stratégie de rachats programmés post-8 ans
  - Comparaison AV Luxembourg vs France
  - Transmission : art. 990 I vs 757 B
- [ ] **Module transmission / succession** :
  - Droits de succession selon lien de parenté
  - Stratégies : donation-partage, démembrement, AV avant 70 ans
  - Simulation transmission pour chaque profil type
- [ ] **Reporting client PDF** (`reportlab` ou `weasyprint`) : rapport prêt à remettre, logo CGP personnalisable.

### 🎨 Fonctionnalités — Priorité basse / Nice-to-have

- [ ] **Interface web Streamlit** (`app.py`) : saisie navigateur + téléchargement Excel + PDF.
- [ ] **Import / Export de portefeuille existant** (CSV Bourse Direct, Degiro, Fortuneo, Linxea) + comparaison allocation actuelle vs cible Boglehead.
- [ ] **Mise à jour automatique des données ETF** via GitHub Actions cron (scraping JustETF / AMF, PR automatique, alerte si perte éligibilité PEA).
- [ ] **Comparateur "Boglehead vs fonds actif"** : démonstration pédagogique de l'écart sur 20-30 ans.
- [ ] **Stress tests historiques** : backtest 2008, 2020, 1973 (stagflation) avec drawdown max et temps de récupération.
- [ ] **Mode "Éducation client"** : onglet `Pédagogie` avec infographies (PEA vs CTO, capitalisant vs distribuant, réplication physique vs synthétique, effet du TER sur 30 ans).
- [ ] **Élargissement hors France** : Belgique (TOB, précompte), Suisse (3e pilier), Luxembourg (contrat de capitalisation). Architecture YAML déjà multi-années.
- [ ] **Assistant IA conversationnel** dans Streamlit : description en langage naturel → choix automatique du profil + recommandations.

### 🛠️ CLI & distribution

- [ ] CLI propre avec `click` ou `typer` :
  ```bash
  bogleheads build --profil 3 --output mon_portefeuille.xlsx
  bogleheads build --all-profils
  bogleheads validate-etf
  bogleheads add-etf --isin IE00B4L5Y983
  ```
- [ ] Packaging PyPI (`pip install bogleheads-fr`)
- [ ] `Dockerfile` pour exécution sans environnement Python local
- [ ] Documentation hébergée via `mkdocs-material` + GitHub Pages
- [ ] Paramétrage par année fiscale : `config/fiscalite/2025.yaml`, `2026.yaml`, `2027.yaml`, sélection par CLI `--year 2026`

### 🗓️ Sprints suggérés

| Sprint | Focus | Livrables |
|---|---|---|
| **S1** (1-2 sem.) | Qualité code | `pyproject.toml`, CI, LICENSE, découpage `excel_builder.py` |
| **S2** (2 sem.) | Optimiseur + Projection MC | Gros bond fonctionnel |
| **S3** (1 sem.) | Glide path + Rebalancement par flux | Différenciation CGP |
| **S4** (2 sem.) | Streamlit + PDF | Passage CLI → produit |
| **S5** (1 sem.) | Import portefeuille + Comparateur | Argumentaire commercial |
| **S6+** | AV avancée, Succession, Refresh auto | Profondeur métier |

---

## 📄 Licence

Ce projet est fourni à titre pédagogique. Les paramètres fiscaux sont indicatifs et doivent être validés par un expert-comptable ou conseiller fiscal agréé avant toute utilisation professionnelle.

**Avertissement réglementaire** : Cet outil ne constitue pas un service d'investissement au sens de la Directive MIF II (2014/65/UE). Son utilisation dans le cadre d'un conseil patrimonial professionnel nécessite que le CGP/CIF soit dûment agréé par l'AMF et respecte ses obligations de conseil personnalisé.

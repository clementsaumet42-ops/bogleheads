# 🏦 Boglehead FR — Outil CGP Multi-Enveloppes 2026

> **Outil pédagogique** pour conseillers en gestion de patrimoine (CGP/CIF) et investisseurs autonomes.
> Génère un fichier Excel complet pour la gestion de portefeuille Boglehead multi-enveloppes fiscales.

> ⚠️ **Avertissement légal** : Cet outil est fourni à titre pédagogique uniquement. Il ne constitue pas un conseil en investissement personnalisé au sens de la Directive MIF II. Tout conseil patrimonial doit être personnalisé par un CIF/CGP agréé AMF. Les paramètres fiscaux 2026 sont indicatifs — valider avec votre expert-comptable.

---

## 🗺️ Workflow CGP en 1 mission (S16 → S17 → S18 → S20)

### Séquence recommandée

```
S20 — Import patrimoine depuis PDF (page 24_Import_Patrimoine) [NOUVEAU]
  - Déposer 1-N relevés PDF (banques, courtiers, assureurs AV)
  - Extraction locale : pdfplumber (texte natif) + OCR Tesseract (fallback scan)
  - Détection automatique de l'émetteur (10 templates)
  - Validation ligne par ligne (mode conservateur)
  - Merge dans la mission active

S16 — Fil conducteur (page 00_Mission_CGP)
  ↓
  1. Créer / sélectionner une mission
  2. Saisir le profil client (04_Profil)
  3. Profilage MIF II (03_Profilage)
  4. Allocation cible (05_Allocation)  ← 💡 pré-calculée automatiquement (S18)
  5. Asset location (07_Asset_Location)
  6. Plan d'exécution (22_Plan_Execution)
  7. Conformité CIF (21_Conformite_CIF)

S17 — Hypothèses traçables
  - Toutes les hypothèses sources citées dans config/hypotheses.yaml
  - Snapshot SHA-256 figé à chaque génération PDF (page 17)
  - Diff entre snapshots disponible dans page Mission CGP

S18 — Densification UX
  - 💾 Auto-save opt-in toutes les 30s (toggle dans sidebar)
  - 💡 Préremplissage intelligent : TMI, profil risque, espérance de vie
  - ⚠️  Validations croisées non bloquantes (incohérences détectées à la saisie)
  - 🚀 Bouton "Tout générer" → ZIP complet en un clic
```

### Import patrimoine PDF — Émetteurs supportés (S20)

| Émetteur | Type | Template |
|---|---|---|
| Bourse Direct | Courtier | `bourse_direct.yaml` |
| Boursorama | Banque/Courtier | `boursorama.yaml` |
| Fortuneo | Banque/Courtier | `fortuneo.yaml` |
| BNP Paribas | Banque | `bnp_paribas.yaml` |
| Société Générale | Banque | `societe_generale.yaml` |
| Crédit Agricole | Banque (toutes caisses) | `credit_agricole.yaml` |
| CIC / Crédit Mutuel | Banque | `cic_cm.yaml` |
| Generali | Assureur AV | `generali.yaml` |
| Linxea | Courtier AV | `linxea.yaml` |
| AXA | Assureur AV | `axa.yaml` |

> Pour ajouter un émetteur ou affiner un template existant : voir [`docs/import_patrimoine.md`](docs/import_patrimoine.md) — aucun code à modifier, uniquement le YAML.

### Gain visé par S18

| Friction supprimée | Gain estimé |
|---|---|
| Perte de saisie après refresh | ~15 min évitées |
| Ressaisie TMI / profil risque | ~20 min évitées |
| Détection tardive d'incohérences | ~15 min évitées |
| Allers-retours pour générer les livrables | ~10 min évitées |
| **Total** | **~1h/mission** |

---

## 📋 Description

Ce projet génère un fichier Excel **`output/portefeuille_bogleheads.xlsx`** contenant 22 onglets dédiés à la gestion d'un portefeuille Boglehead en France, avec optimisation multi-enveloppes fiscales (PEA, PER, PEE, CTO, Contrat Cap IS).

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
- ⭐ **Optimiseur d'allocation intégré** (Sprint S2) : allocation cible Markowitz (scipy QP) + asset location MILP (pulp) avec contraintes fiscales et profil de risque personnalisé

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
│   ├── fiscalite/              ← Package fiscal exhaustif (13 modules)
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

## ⭐ Optimiseur d'allocation intégré (S2)

Module `src/optimiseur_allocation.py` — Allocation mathématiquement optimale en deux modes chaînables.

### Mode A — Allocation cible (Markowitz via scipy)

Optimise les poids par classe d'actifs (actions USA, Dev ex-USA, Émergents, Obligations, REIT, Or, Monétaire) en minimisant `variance - λ × rendement_attendu`.

```python
from src.optimiseur_allocation import calculer_allocation_cible, charger_config_optimiseur

config = charger_config_optimiseur()
profil = {
    "profil_aversion_risque": "dynamique",
    "age": 45,
    "contraintes_personnalisees": {
        "exposition_usa_max": 0.50,
        "exposition_em_max": 0.15,
    },
}
poids = calculer_allocation_cible(profil, config)
# → {"actions_usa": 0.50, "actions_dev_ex_usa": 0.05, "actions_em": 0.15, ...}
```

### Mode B — Asset location (MILP via pulp)

Ventile chaque classe entre les enveloppes disponibles en minimisant les frais annuels totaux (TER + frais gestion) sous contraintes de plafonds et d'éligibilité.

```python
from src.optimiseur_allocation import optimiser_portefeuille_complet

res = optimiser_portefeuille_complet(profil_dict, config)
# res["resultat_mode_b"]["cout_annuel_optimise"] < res["resultat_mode_b"]["cout_annuel_naif"]
```

### Configuration (`config/optimiseur.yaml`)

```yaml
classes_actifs:
  actions_usa:
    rendement_attendu_annuel: 0.078
    volatilite_annuelle: 0.18
    frais_ter_moyen: 0.0007
    eligible_pea: true

profils_aversion_risque:
  defensif:   { lambda: 0.2, actions_max: 0.40 }
  equilibre:  { lambda: 0.5, actions_min: 0.40, actions_max: 0.70 }
  dynamique:  { lambda: 0.8, actions_min: 0.70, actions_max: 0.90 }
  agressif:   { lambda: 1.0, actions_min: 0.85 }
```

### Profils enrichis (`config/profils_clients.yaml`)

```yaml
profil_1_cadre:
  profil_aversion_risque: "dynamique"
  contraintes_personnalisees:
    exposition_em_max: 0.15
    exposition_usa_max: 0.50
```

### Onglet Excel `Allocation_Optimisee`

Généré automatiquement avec :
- Mode A : allocation cible + rendement/volatilité/Sharpe attendus
- Mode B : tableau croisé classe × enveloppe (montants en €)
- Comparaison coût optimisé vs coût naïf (tout CTO)

### Fallback gracieux

Si `scipy` ou `pulp` sont indisponibles, le module bascule automatiquement sur les heuristiques Boglehead avec un warning log.

```bash
# Activer l'extra optim pour PuLP
pip install -e ".[optim]"
# Installer scipy pour le solveur QP Mode A
pip install scipy
```

---

## 💰 Moteur Fiscal Exhaustif (S7)

Module `src/fiscalite/` — Moteur fiscal complet avec cascade détaillée et sources juridiques.

### Architecture du package

Le package `src/fiscalite/` est organisé en modules spécialisés :

```
src/fiscalite/
├── __init__.py              ← API publique + backward compatibility
├── constantes.py            ← Taux PS 18.6%, PFU 12.8%, barème IR 2026, etc.
├── cascade.py               ← Pydantic models (ResultatFiscal, LigneCalcul)
├── prelevements_sociaux.py  ← PS 18.6% (Art. L.136-8 CSS)
├── tmi.py                   ← Barème IR, quotient familial, décote
├── pfu.py                   ← PFU avec CEHR et CDHR
├── pea.py                   ← PEA et PEA-PME (durées 0-2/2-5/>5 ans)
├── per.py                   ← PER (déduction, sortie capital/rente)
├── assurance_vie.py         ← AV (complexité date 27/09/2017, seuils, abattements)
├── cto_ir.py                ← CTO particulier (PFU ou barème)
├── cto_is.py                ← CTO société IS + détection MTM
├── contrat_cap_is.py        ← Contrat capitalisation IS (Art. 238 septies E)
└── is_calc.py               ← IS 15%/25% (Art. 219 CGI)
```

### Cascade fiscale avec sources juridiques

Chaque calcul retourne un objet `ResultatFiscal` avec :

```python
from src.fiscalite import calculer_fiscalite_operation, ResultatFiscal

operation = {
    "type": "retrait_pea",
    "montant_brut": 20000,
    "gains": 10000,
    "duree_detention": 6.0,
}

profil = {"situation": "celibataire", "rfr": 50000, "tmi": 0.30}

result: ResultatFiscal = calculer_fiscalite_operation(operation, profil)

# Cascade détaillée ligne par ligne
for ligne in result.cascade:
    print(f"{ligne.libelle}: {ligne.montant:.2f} € ({ligne.source})")

# Articles cités
print(result.articles_cites)  # ['Art. 150-0 A CGI', 'Art. L.136-8 CSS']

# Avertissements
print(result.avertissements)  # ['PEA > 5 ans : exonération IR']
```

### Enveloppes fiscales couvertes

#### PEA / PEA-PME
- Durée < 2 ans : IR au TMI + PS 18.6%
- Durée 2-5 ans : IR 12.8% + PS 18.6%
- Durée > 5 ans : Exonération IR, PS 18.6% uniquement
- Cas force majeure : exonération totale
- Plafonds : 150k€ (PEA) + 225k€ (PEA-PME), cumul max 225k€

#### Assurance Vie
- < 4 ans : PFU 12.8% + PS, pas d'abattement
- 4-8 ans : PFU 12.8% + PS, abattement 4 600€/9 200€
- > 8 ans : complexité date 27/09/2017
  - Avant 27/09/2017 : PFL 7.5% ou barème
  - Après 27/09/2017 : 7.5% si encours < 150k€/300k€, sinon 12.8%
- Fonds euro : PS déjà prélevés annuellement
- AV Luxembourg : fiscalité française identique

#### PER
- Entrée : déduction 10% revenus (plafond 4 399€ à 35 194€)
- Sortie capital :
  - Versements déduits : IR au TMI sur tout + PS sur gains
  - Versements non déduits : IR au TMI sur gains + PS sur gains
- Sortie rente : RVTO selon âge
- 6 cas déblocage anticipé (Art. L.224-4 CMF)

#### CTO Particulier (IR)
- PFU par défaut : 12.8% + 18.6% = 31.4%
- Option barème : TMI + 18.6% PS (abattement 40% sur dividendes)
- Option irrévocable pour l'année fiscale

#### CTO Société IS
- **Piège Mark-to-Market** (Art. 209-0 A CGI)
  - OPCVM détenus à > 90% par sociétés IS
  - Imposition des PV latentes CHAQUE ANNÉE
  - Détection automatique : `detecter_piege_mtm()`
- Alternative : Contrat de capitalisation IS

#### Contrat Capitalisation IS
- Base taxable : 105% × TME × prime (Art. 238 septies E)
- IS sur base forfaitaire annuelle
- Régularisation à la cession
- Avantageux si rendement > TME

### CEHR et CDHR

#### CEHR (Art. 223 sexies CGI)
- Célibataire : 3% (RFR 250-500k), 4% (RFR > 500k)
- Couple : 3% (RFR 500k-1M), 4% (RFR > 1M)

#### CDHR (Art. 223 terdecies CGI, LF 2025)
- Plancher 20% d'imposition effective sur RFR
- S'applique si RFR > 250k€ (célibataire) ou 500k€ (couple)
- Complète CEHR pour atteindre le plancher

### Pages Streamlit

#### 12_Simulateur_Fiscal.py
Simule une opération fiscale avec cascade détaillée :
- Sélection type d'opération (CTO, PEA, AV, PER)
- Paramètres de l'opération
- Affichage cascade, articles cités, avertissements

#### 13_Comparateur_Enveloppes.py
Compare PEA vs CTO vs AV vs PER sur un horizon donné :
- Tableau comparatif capital net
- Graphique interactif
- Insights automatiques

#### 14_Alertes_Fiscales.py
Détecte les pièges fiscaux :
- Mark-to-Market OPCVM à l'IS
- PEA < 5 ans (pas d'avantage)
- AV < 8 ans (pas d'abattement)
- Plafonds PEA/PEA-PME

### Tests

**342 tests unitaires** (274 baseline + 68 nouveaux) :

```bash
pytest tests/test_fiscalite*.py -v
```

Couverture :
- `test_fiscalite_constantes.py` : constantes (TAUX_PS, PFU, IS)
- `test_fiscalite_tmi.py` : barème IR, quotient familial, décote
- `test_fiscalite_pea.py` : durées PEA, plafonds, cas force majeure
- `test_fiscalite_av.py` : AV complexe (15 tests)
- `test_fiscalite_cto_is.py` : détection MTM, comparatif contrat cap
- `test_fiscalite_contrat_cap_is.py` : base forfaitaire, avantage
- `test_fiscalite_cehr_cdhr.py` : CEHR tranches, CDHR plancher 20%

### Configuration

Fichier enrichi `config/fiscalite/2026.yaml` avec sources juridiques complètes.

### Backward Compatibility

L'ancienne API `src/fiscalite.py` est entièrement préservée :

```python
from src.fiscalite import charger_params_fiscaux, calculer_pfu, calculer_is
# Fonctionne exactement comme avant
```

Tous les tests existants passent sans modification.

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

## 📄 PDF client 13 pages (S3)

Module `src/pdf_builder.py` — Génération d'un livrable PDF professionnel remis au client par le CGP.

### Générer les PDFs

```bash
# Tous les profils
python build_pdf.py

# Un seul profil
python build_pdf.py --profil PROFIL_1_CADRE_SUP
```

Sortie : `output/<code_profil>_<YYYYMMDD>.pdf`

### Structure du PDF — 13 pages

| # | Page | Contenu |
|---|---|---|
| 1 | Couverture | Logo cabinet (ou fallback texte), nom client, date |
| 2 | Synthèse exécutive | Patrimoine total, allocation actuelle vs cible, économie fiscale, 3 actions clés |
| 3 | Profil client | Situation, objectifs, horizon, TMI, contraintes |
| 4 | Patrimoine actuel | Tableau par enveloppe + **graphique camembert matplotlib** |
| 5 | Philosophie Boglehead | 3 principes : ETF passifs, diversification, low-cost |
| 6 | Allocation cible | Output `calculer_allocation_cible()` (S2), bornes et justification |
| 7 | Asset location | Matrice classes × enveloppes via S2 Mode B, logique fiscale |
| 8 | Univers ETF | 15 ETF : ISIN, TER, éligibilité PEA/AV (depuis `univers_etf.yaml`) |
| 9 | Projection Monte-Carlo | **Graphique matplotlib** 30 ans médiane + P10/P90 |
| 10 | Plan de rebalancement | 3 étapes : gratuit → flux → vente (S3.6 si dispo, sinon fallback) |
| 11 | Fiscalité & transmission | TMI, abattements AV, PER déduction, transmission |
| 12 | Suivi recommandé | Calendrier trimestriel, KPIs, alertes |
| 13 | Mentions légales & annexes | Hypothèses, avertissement AMF, glossaire |

### API principale

```python
from src.pdf_builder import generer_pdf, charger_config_pdf
from src.schemas import charger_et_valider

config_pdf = charger_config_pdf()  # charge config/pdf_cabinet.yaml
profils = charger_et_valider("profils_clients.yaml")
profil = profils.profils[0]

resultat = generer_pdf(profil, config_pdf, "output/profil1.pdf")
# ResultatPDF(chemin=..., taille_octets=110000, nb_pages=13, ...)
```

### Configuration cabinet (`config/pdf_cabinet.yaml`)

```yaml
cabinet:
  nom: "Cabinet Saumet Patrimoine"
  logo_path: "assets/logo_cabinet.png"   # optionnel, fallback texte si absent
  numero_orias: "XXXXXXXXXXXX"
  mention_conformite: "CIF membre de la CNCIF"

style:
  couleur_primary: "#1a4d8f"
  couleur_accent:  "#d4a017"
  marges_cm: 2.0

footer:
  mention_legale: "Document confidentiel — ne pas diffuser"
```

### Exemples committés

6 PDFs exemple dans `examples/` (un par profil, 13 pages, 100–120 Ko chacun) :

```
examples/
├── PROFIL_1_CADRE_SUP_exemple.pdf
├── PROFIL_2_DIRIGEANT_GG_exemple.pdf
├── PROFIL_3_DIRIGEANT_PME_exemple.pdf
├── PROFIL_4_PROFESSION_LIBERALE_exemple.pdf
├── PROFIL_5_JEUNE_CADRE_exemple.pdf
└── PROFIL_6_PRE_RETRAITE_exemple.pdf
```

### Fallbacks gracieux

| Situation | Comportement |
|---|---|
| Logo absent / chemin invalide | Affichage du nom du cabinet en texte |
| S2 optimiseur indisponible | Allocation indicative depuis le profil YAML |
| S3.6 rebalancement_optimal absent | Fallback sur `src.rebalancement` classique |
| `src.projection` indisponible | Monte-Carlo interne simplifié |

---

 Il contient **70 ETF** couvrant toutes les classes d'actifs d'un portefeuille Boglehead.

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
5. Renseigner les champs S11-C : `replication`, `domicile_iso`, `exposition_geo`
6. Lancer les tests de validation :

```bash
pytest tests/test_univers_etf.py -v
```

### TER effectif (S11-C) — Drag fiscal intra-NAV

Le **TER effectif** = TER affiché + drag de withholding intra-NAV.

Les ETF physiques détenant des actions étrangères subissent une **retenue à la source (withholding tax)** prélevée dans la valeur liquidative, invisible sur le relevé client mais grève la performance de **0 à 60 bps/an**.

| Réplication | Domicile | Exposition | Retenue eff. | Yield déf. | Drag estimé |
|---|---|---|---|---|---|
| `synthetique_swap` | * | * | 0 % | — | **0 bps** |
| `physique_full/sampling` | IE | US | 15 % | 1,5 % | ~22 bps |
| `physique_full/sampling` | LU | US | 30 % | 1,5 % | ~45 bps |
| `physique_full/sampling` | FR/DE | US | 15 % | 1,5 % | ~22 bps |
| physique | * | Monde_dev | 15 % pondéré | 1,8 % | ~27 bps |
| physique | * | Monde_ACWI | 14 % pondéré | 1,9 % | ~27 bps |
| physique | * | Emergents | 10 % pondéré | 2,5 % | ~25 bps |
| physique | * | Europe / France | 0 % | 3,0 % | **0 bps** |
| physique | * | Japon | 15 % | 2,0 % | ~30 bps |

> 🔑 **Logique clé** : Les ETF synthétiques (swap) annulent totalement la withholding sur la jambe répliquée.
> Les ETF physiques domiciliés en Irlande bénéficient du traité IE-US (15 % au lieu de 30 %).

La page **Univers ETF** affiche les colonnes `TER affiché`, `Drag fiscal (bps)`, `TER effectif`
et trie par défaut sur le **TER effectif ascendant**. Un badge 🔴 signale les ETF avec drag > 20 bps.

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
| `Allocation_Optimisee` | ⭐ Allocation cible Markowitz (Mode A) + ventilation MILP par enveloppe (Mode B) + comparaison coût optimisé vs naïf |

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

## 🌐 Webapp Streamlit (S4)

Lancez l'interface web interactive en une commande :

```bash
pip install -e ".[web,optim]"
streamlit run app.py
```

### Architecture multi-pages

```
🏠 Accueil → 👤 Profil → 🎯 Allocation → 🏦 Asset Loc → 📈 Monte-Carlo → 🔄 Rebal → 📥 Exports
```

| Page | Fonctionnalité |
|---|---|
| 🏠 Accueil | KPIs (nb profils, enveloppes, ETF) + call-to-action |
| 👤 Profil client | Formulaire interactif ou chargement YAML — validation Pydantic live |
| 🎯 Allocation cible | Sliders contraintes (USA max, EM max) → recalcul Markowitz en live |
| 🏦 Asset Location | Heatmap Plotly classes × enveloppes, comparaison coût optimisé vs naïf |
| 📈 Monte-Carlo | Fan chart P10/médiane/P90, probabilité d'atteinte de l'objectif |
| 🔄 Rebalancement | Plan 3 étapes (arbitrages gratuits → flux → ventes), économie fiscale |
| 📥 Téléchargements | Boutons Excel (22 onglets) et PDF client (13 pages) téléchargeables |

Voir `docs/webapp.md` pour le guide utilisateur complet.

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
- [x] **Reporting client PDF** (`reportlab`) : rapport 13 pages prêt à remettre, logo CGP personnalisable, graphiques matplotlib, fallbacks gracieux.

### 🎨 Fonctionnalités — Priorité basse / Nice-to-have

- [x] **Interface web Streamlit** (`app.py`) : 7 pages interactives — profil, allocation Markowitz, asset location, Monte-Carlo, rebalancement, exports Excel+PDF. Deploy-ready (Docker). ← **S4 ✅**
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
| **S3.6** (1 sem.) | Rebalancement optimal MILP | Cascade fiscale 3 étapes |
| **[x] S3** (1 sem.) | PDF client 13 pages | `build_pdf.py`, reportlab, matplotlib, 6 exemples |
| **[x] S4** (2 sem.) | Streamlit | **7 pages interactives, Docker, 34 tests** |
| **S5** (1 sem.) | Import portefeuille + Comparateur | Argumentaire commercial |
| **S6+** | AV avancée, Succession, Refresh auto | Profondeur métier |
| **[x] S9** (1 sem.) | Backtest historique | Moteur backtest mensuel, 4 modes, 5 portefeuilles |
| **[x] S11-AB** (1 sem.) | Crédibilité chiffrée | Sources Markowitz, audit ETF, visibilité éligibilité, utilité rebalancement |

---

## 🧪 Crédibilité chiffrée (S11-A + S11-B)

Sprint S11 comble 4 lacunes de crédibilité identifiées par un expert-comptable / CIF :

### 1. Sources Markowitz documentées (A)

Les rendements espérés μ, volatilités σ et corrélations ρ sont maintenant **entièrement documentés** avec sources vérifiables :

- `config/optimiseur.yaml` : section `metadonnees` + `rendements_esperes` avec `source_specifique` et `intervalle_confiance_95` pour chaque classe
- `src/optimiseur/config_schemas.py` : validation Pydantic (`CalibrationMetadata`, `RendementEspere`, `ConfigOptimiseurEnrichi`)
- `docs/methodologie_markowitz.md` : documentation de 3-4 pages (méthode, sources, limites, shrinkage)
- Page `05_Allocation.py` : expander « 📖 Sources et hypothèses » avec tableau μ/σ par classe et avertissements AMF
- Option shrinkage Ledoit-Wolf disponible mais désactivée par défaut (`appliquer_shrinkage=True`)

### 2. Éligibilité ETF visible (B)

L'éligibilité PEA/AV/PER/CTO est maintenant **visible dans l'UI** :

- Page `12_Univers_ETF.py` : filtres par enveloppe (intersection), classe d'actifs, TER max, AUM min
- Tableau avec icônes ✅/❌ par enveloppe, DICI cliquable, badge couleur « Vérifié »
- Export CSV du tableau filtré
- Liens depuis `05_Allocation.py` et `07_Asset_Location.py` → `12_Univers_ETF.py`

### 3. Audit qualité ETF (B)

- Script `tools/audit_univers_etf.py` : ISIN Luhn, TER, AUM, TD, `derniere_verification`, URL DICI
- 10+ ETFs phares marqués `derniere_verification: 2025-04-25`
- Workflow `.github/workflows/audit_etf.yml` (cron hebdomadaire, issue auto en cas de FAIL)
- Champs `derniere_verification`, `audit_status`, `audit_notes` dans `src/schemas.py`

### 4. Utilité du rebalancement visible (C)

- Page `09_Rebalancement.py` : panneau « 🔍 Pourquoi rebalancer ? » avec simulation drift 12 mois
- Verdict 💚/🟡/🔴 selon la dérive calculée
- Bilan coût/bénéfice estimatif avec ratio coût/bénéfice

### Sources μ/σ

| Source | Couverture |
|--------|-----------|
| JPM LTCMA 2026 | Toutes classes sauf OR/REIT |
| Vanguard Capital Markets Model 2026 | Actions développées |
| Research Affiliates CMA Q1 2026 | Dev ex-USA, EM |
| BlackRock Investment Institute 2026 | Validation croisée |

Voir : [`docs/methodologie_markowitz.md`](docs/methodologie_markowitz.md)

---

## Charte graphique & crédits (S19)

L'interface suit la charte graphique Private Banking décrite dans [`docs/charte-graphique.md`](docs/charte-graphique.md).

### Typographie
- **EB Garamond** (titres) — Georg Duffner — [OFL License](https://fonts.google.com/specimen/EB+Garamond)
- **Inter** (corps) — Rasmus Andersson — [OFL License](https://fonts.google.com/specimen/Inter)

### Icônes
- **Lucide Icons** — Lucide Contributors — [ISC License](https://lucide.dev/license)
  Icônes embarquées dans `assets/icons/` : chevron-right, check, alert-circle, info, download, file-text, users, briefcase, trending-up, pie-chart, calendar, clock, archive, external-link, settings, arrow-right, eye, printer

---

## Cas de test dogfood

Un cas fictif complexe ("Famille Rousseau-Marchand") est disponible dans [`dogfood/cas_rousseau/`](dogfood/cas_rousseau/README.md) pour tester le tool de bout en bout sans client réel.

Le cas couvre 5 enveloppes importables via S20, 18 pièges fiscaux et réglementaires scorables, et une fixture YAML pour les tests de régression.

- [Mode d'emploi et contenu](dogfood/cas_rousseau/README.md)
- [Grille de scoring (18 pièges)](dogfood/cas_rousseau/grille_scoring.md)
- [Fixture E2E YAML](tests/fixtures/cas_rousseau.yaml)

---

## Licence

Ce projet est fourni à titre pédagogique. Les paramètres fiscaux sont indicatifs et doivent être validés par un expert-comptable ou conseiller fiscal agréé avant toute utilisation professionnelle.

**Avertissement réglementaire** : Cet outil ne constitue pas un service d'investissement au sens de la Directive MIF II (2014/65/UE). Son utilisation dans le cadre d'un conseil patrimonial professionnel nécessite que le CGP/CIF soit dûment agréé par l'AMF et respecte ses obligations de conseil personnalisé.

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
│   └── profils_clients.yaml   ← 6 profils clients fictifs
├── src/
│   ├── fiscalite.py            ← Calculs PFU, IS, PEA, PER, CEHR, CDHR
│   ├── enveloppes.py           ← Règles métier enveloppes
│   ├── allocation.py           ← Allocation cible Boglehead
│   ├── asset_location.py       ← Optimisation asset location
│   ├── rebalancement.py        ← Rebalancement et coûts fiscaux
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

## 📈 Univers ETF

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

## 📄 Licence

Ce projet est fourni à titre pédagogique. Les paramètres fiscaux sont indicatifs et doivent être validés par un expert-comptable ou conseiller fiscal agréé avant toute utilisation professionnelle.

**Avertissement réglementaire** : Cet outil ne constitue pas un service d'investissement au sens de la Directive MIF II (2014/65/UE). Son utilisation dans le cadre d'un conseil patrimonial professionnel nécessite que le CGP/CIF soit dûment agréé par l'AMF et respecte ses obligations de conseil personnalisé.

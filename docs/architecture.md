# Architecture — Outil CGP Bogleheads France

## Vue d'ensemble

```
bogleheads/
├── config/                  # Paramètres YAML — données de référence
│   ├── fiscalite_2026.yaml  # Taux fiscaux France 2026
│   ├── enveloppes.yaml      # 6 enveloppes d'investissement
│   └── univers_etf.yaml     # ~25 ETFs Bogleheads France
├── src/                     # Modules Python
│   ├── fiscalite.py         # Calculs fiscaux (PFU, CEHR, CDHR, IS)
│   ├── enveloppes.py        # Dataclasses enveloppes + calcul impôt sortie
│   ├── allocation.py        # AllocationCible + règle âge-en-obligations
│   ├── asset_location.py    # AssetLocator — priorisation enveloppes
│   ├── rebalancement.py     # Bandes de tolérance + coût fiscal arbitrage
│   └── excel_builder.py     # Constructeur classeur openpyxl (8 feuilles)
├── tests/                   # Tests pytest
│   └── test_fiscalite.py    # Tests unitaires fiscalité
├── docs/                    # Documentation
│   ├── regles_fiscales.md   # Référentiel fiscal avec sources légales
│   └── architecture.md      # Ce fichier
├── output/                  # Fichiers Excel générés (gitignorés)
│   └── .gitkeep
├── build_excel.py           # Point d'entrée — génère le classeur
└── requirements.txt         # Dépendances Python
```

## Flux de données

```
YAML (config/)
    │
    ▼
Python (src/)
    ├── fiscalite.py    → Calculs PFU, CEHR, CDHR, IS, mark-to-market
    ├── enveloppes.py   → Objets enveloppes + méthodes calcul fiscal
    ├── allocation.py   → Profils + règle âge-en-obligations
    ├── asset_location.py → Priorités enveloppe par classe d'actifs
    └── rebalancement.py  → Bandes tolérance + recommandations
         │
         ▼
    excel_builder.py    → Assemblage des 8 feuilles Excel
         │
         ▼
output/portefeuille_bogleheads.xlsx
```

## Modules

### `src/fiscalite.py`
Fonctions pures de calcul fiscal. Charge le YAML au démarrage du module.
- `calculer_pfu(montant_pv)` → PFU 31.4 %
- `calculer_cehr(rfr, situation)` → CEHR 3 %/4 %
- `calculer_cdhr(rfr, impot)` → CDHR plancher 20 %
- `calculer_is(benefice)` → IS PME 15 %/25 %
- `calculer_mark_to_market_is(v_debut, v_fin)` → Piège art. 209-0 A
- `calculer_base_taxable_contrat_cap_is(prime, tme)` → Base forfaitaire

### `src/enveloppes.py`
Dataclass `Enveloppe` chargée depuis YAML. Méthode `calculer_impot_sortie(gain, tmi)`.

### `src/allocation.py`
`AllocationCible` avec méthodes :
- `depuis_profil(profil, age)` — profils prédéfinis
- `depuis_age_en_obligations(age, variante)` — règle Bogleheads
- `calculer_bornes_tolerance(patrimoine)` — bandes ±5 %
- `decomposer_actions(...)` / `decomposer_obligations(...)`

### `src/asset_location.py`
`AssetLocator` avec règles de priorité par classe d'actifs. Structure prête pour
intégration future de `cvxpy` (optimisation sous contraintes).

### `src/rebalancement.py`
- `calculer_bandes_tolerance(pct_cible, methode)` — absolu ou Swedroe (±25 % relatif)
- `calculer_cout_fiscal_arbitrage(pv_latente, taux)` — coût d'opportunité
- `recommander_rebalancement(actuel, cible, total)` — synthèse d'actions

### `src/excel_builder.py`
Fonction principale `construire_workbook(fiscalite, enveloppes, etf_data)`.
Crée 8 feuilles :

| # | Feuille | Contenu |
|---|---------|---------|
| 1 | Paramètres_Client | Champs éditables (âge, TMI, RFR, patrimoine) |
| 2 | Paramètres_Fiscalité_2026 | Taux fiscaux 2026 avec sources légales |
| 3 | Enveloppes | Synthèse des 6 enveloppes |
| 4 | Univers_ETF | ~25 ETFs avec éligibilités |
| 5 | Allocation_Cible | Profils + règle âge-en-obligations |
| 6 | Asset_Location_Matrice | Matrice ETF × Enveloppe, Solveur Excel |
| 7 | Rebalancement | Bandes tolérance + coût fiscal |
| 8 | Reporting_Client | Synthèse + valeur ajoutée fiscale |

## Choix techniques

### Openpyxl
- Tables structurées (`Table`, `TableStyleInfo`) pour navigation Excel
- `DataValidation` pour dropdowns (TMI, profil, situation familiale)
- `ConditionalFormatting` pour alertes visuelles (hors bandes = rouge)
- Cellules grisées pour contraintes d'éligibilité (Asset Location)

### YAML pour la configuration
Les taux fiscaux, enveloppes et ETFs sont externalisés en YAML pour permettre
la mise à jour annuelle sans toucher au code Python.

### Extension future — cvxpy
Le module `asset_location.py` est structuré pour accueillir une optimisation
sous contraintes via `cvxpy` :
```python
# TODO : optimisation sous contraintes
import cvxpy as cp
x = cp.Variable((n_etfs, n_enveloppes), boolean=True)
# Objectif : maximiser VAN nette d'impôts
# Contraintes : plafonds enveloppes, éligibilités, allocations cibles
```

## Tests

```bash
pytest tests/ -v
```

Tests couverts :
- PFU (art. 200 A CGI)
- CEHR (art. 223 sexies CGI)
- CDHR (LF 2025 — À VALIDER 2026)
- IS PME (art. 219 CGI)
- Mark-to-market IS (art. 209-0 A CGI)
- Contrat capitalisation IS (art. 38 sexdecies GB Ann. III CGI)

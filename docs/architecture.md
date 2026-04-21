# Architecture du projet Boglehead FR

## Vue d'ensemble

```
bogleheads/
├── build_excel.py          ← Point d'entrée principal
├── requirements.txt        ← Dépendances Python
├── config/                 ← Données de configuration (YAML)
│   ├── fiscalite_2026.yaml
│   ├── enveloppes.yaml
│   ├── univers_etf.yaml
│   └── profils_clients.yaml
├── src/                    ← Code source Python
│   ├── fiscalite.py        ← Calculs fiscaux (PFU, IS, PEA, PER, CEHR…)
│   ├── enveloppes.py       ← Règles métier enveloppes
│   ├── allocation.py       ← Allocation cible Boglehead
│   ├── asset_location.py   ← Asset location multi-enveloppes
│   ├── rebalancement.py    ← Rebalancement et coûts fiscaux
│   └── excel_builder.py    ← Génération du fichier Excel (openpyxl)
├── docs/                   ← Documentation
├── tests/                  ← Tests pytest
└── output/                 ← Fichier Excel généré (ignoré par git)
```

## Flux de données

```
YAML configs ──→ src/*.py modules ──→ excel_builder.py ──→ output/*.xlsx
     │                  │
     └─── tests/ ←──────┘
```

## Modules principaux

### `src/fiscalite.py`
Calculs fiscaux purs, sans effet de bord :
- `calculer_pfu()` : PFU 31,4% sur dividendes/PV
- `calculer_is()` : IS 15%/25% avec seuil 42 500 €
- `calculer_base_taxable_contrat_cap_is()` : Base forfaitaire art. 238 septies E
- `avantage_fiscal_pea()` : Comparatif PEA vs CTO
- `calculer_avantage_per()` : Simulation PER vs CTO sur horizon

### `src/excel_builder.py`
Génère le fichier Excel avec 17 onglets via openpyxl.
Chaque onglet est une fonction `creer_onglet_*()`.
La fonction `generer_excel()` orchestre l'ensemble.

## Dépendances

| Package | Rôle |
|---|---|
| `openpyxl` | Génération Excel (styles, tableaux, formules) |
| `pandas` | Manipulation de données tabulaires |
| `pyyaml` | Lecture des fichiers de configuration YAML |
| `pytest` | Framework de tests unitaires |

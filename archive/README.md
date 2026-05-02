# Archive — Modules non alignés sur le parcours mission EC

Ce dossier contient les modules archivés suite au pivot stratégique vers les experts-comptables (EC) inscrits CIF conseillant des dirigeants de PME avec holding à l'IS.

## Pourquoi ce pivot ?

Le projet est repositionné. Cible unique : **experts-comptables (EC) inscrits CIF qui conseillent des dirigeants de PME avec holding à l'IS** (patrimoine financier 1,5-15 M€, trésorerie excédentaire en société).

Les modules archivés ici couvrent des fonctionnalités pertinentes pour un outil grand public (Monte-Carlo, glide path, backtest, 22 onglets Excel, 70 ETF, profils types fictifs) mais non alignées sur le parcours mission EC décrit dans `src/mission/lifecycle.py`.

## Règles

- ❌ Aucun nouveau développement ne doit être fait dans `archive/`
- ✅ Ces modules sont conservés pour l'historique git
- ✅ Les tests correspondants sont marqués `@pytest.mark.skip` (aucun test supprimé)

## Date d'archivage

Archivé le 2026-04-30. Dernier commit "musée" : voir `git log --oneline archive/`.

## Modules archivés

| Dossier | Origine | Raison |
|---|---|---|
| `monte_carlo/` | `src/projection.py` | Non aligné parcours mission EC |
| `glide_path/` | `src/glide_path.py` | Non aligné parcours mission EC |
| `backtest/` | `src/backtest/`, `build_backtest.py`, `data/historiques/` | Non aligné parcours mission EC |
| `excel_builder_complet/` | `src/excel_builder.py`, `src/excel/` | 22 onglets non utiles pour mission EC |
| `profils_types_fictifs/` | `config/profils_clients.yaml` | Profils fictifs grand public |
| `univers_70_etf/` | `config/univers_etf.yaml` | Univers 70 ETF non pertinent EC |
| `pedagogie_boglehead/` | `docs/*.md` (pédagogiques) | Documentation Boglehead générique |
| `streamlit_pages_archive/` | Pages Streamlit non liées au parcours mission | Non alignées parcours mission EC |

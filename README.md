# HoldIS Advisor — Outil de mission CIF pour experts-comptables

> L'outil de production de missions de conseil patrimonial pour experts-comptables
> qui conseillent des dirigeants de PME avec holding à l'IS.

## Pour qui

Expert-comptable inscrit CIF qui veut industrialiser ses missions patrimoniales
auprès de dirigeants PME (patrimoine financier 1,5–15 M€, holding IS, trésorerie
excédentaire). Pas pour le grand public, pas pour les CGP généralistes, pas pour
les particuliers en autonomie.

## Pourquoi

Aucun outil du marché ne traite proprement :
- Le piège mark-to-market (Art. 209-0 A CGI) sur OPCVM en holding IS
- Le contrat de capitalisation IS comme alternative chiffrée
- L'asset location MILP avec contrainte fiscale IS
- L'industrialisation des livrables CIF (DER + LM + RAA MIF II signés eIDAS)

## Le parcours mission en 6 étapes

| # | Étape | Output | Durée |
|---|---|---|---|
| 0 | Qualification | Score WTF 0–10 (8 questions) | 30 min |
| 1 | Onboarding | DER + LM + profilage MIF II signés | 2h |
| 2 | Diagnostic fiscal | Alertes chiffrées (12 règles IS) | 4h |
| 3 | Recommandations | Allocation cible + asset location MILP | 2h |
| 4 | Plan d'action | Cascade 12 mois trimestrielle | 2h |
| 5 | Livrables signés | RAA MIF II + classeur PDF eIDAS | 1h |
| 6 | Suivi annuel | Revue + delta fiscal réalisé | 2h/an |

Mission complète : ~4 semaines, livrable signé, 50–100 k€/an d'opportunités fiscal chiffrées.

## Architecture

```
src/
├── mission/          # Orchestration du cycle de vie mission
├── fiscalite_is/     # Moteur IS : MTM, cap IS, TLH, 150-0 B ter
├── allocation/       # Asset location MILP + allocations standard
├── plan_action/      # Cascade 12 mois trimestrielle
├── livrables/        # DER, LM, RAA MIF II, PDF diagnostic
├── alertes/          # 12 règles dirigeant IS (sur 40)
├── suivi/            # Revue annuelle + delta fiscal
├── fiscalite/        # Moteur fiscal complet (13 modules)
├── cif/              # DER, LM, RAA, journal, signature
├── profilage/        # Profilage MIF II
└── import_patrimoine/ # Import PDF S20 (10 templates)
```

## État actuel

| Composant | Statut |
|---|---|
| Cœur fiscal IS (S7, S11-C) | ✅ Opérationnel |
| DER + LM + RAA (S14) | ✅ Opérationnel |
| Asset location MILP (ex-S2) | ✅ Opérationnel |
| Import patrimoine PDF (S20) | ✅ Opérationnel |
| Squelette `src/mission/` | 🚧 Implémentation S+1 |
| Modules archivés | 📦 Voir `archive/README.md` |

## Lancement

```bash
pip install -e ".[dev]"
streamlit run app.py
```

## Tests

```bash
pytest
ruff check . && ruff format --check .
```

## Modules archivés

Les modules non alignés sur le parcours mission EC (Monte-Carlo, glide path,
backtest, 22 onglets Excel, 70 ETF, profils types fictifs, pages Streamlit
pédagogiques) sont conservés dans `archive/` pour l'historique git.
Voir `archive/README.md`.

## Avertissement réglementaire

Cet outil produit des livrables réglementaires (DER, LM, RAA MIF II). Son usage
en mission CIF facturée nécessite une RC Pro produit et un audit du moteur fiscal
par un fiscaliste senior. Voir `docs/audit_fiscal_externe.md` (à venir).

## Licence

MIT

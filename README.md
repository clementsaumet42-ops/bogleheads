# Sextant — Atelier de mission patrimoniale Bogleheads pour experts-comptables CIF

> L'outil qui industrialise les missions de conseil en investissement financier
> pour les experts-comptables inscrits CIF, en pilotant un patrimoine selon la
> philosophie Bogleheads adaptée au cadre fiscal français.

## Pour qui

**Experts-comptables inscrits CIF** qui conduisent des missions patrimoniales
récurrentes pour leurs clients (dirigeants, professions libérales, cadres
patrimoniaux, foyers aisés). Pas pour le grand public en autonomie, pas pour
les CGP généralistes hors cabinet EC, pas pour la gestion sous mandat.

## La conviction produit

Un patrimoine se pilote comme un portefeuille indiciel diversifié — **philosophie
Bogleheads** : allocation cible explicite, ETF passifs à frais bas, horizon long,
pas de market timing, rebalancement discipliné. Mais en France, cette philosophie
se heurte à trois frictions que les outils anglo-saxons ignorent :

1. **La fiscalité d'enveloppe** — PEA, AV, CTO, PEE/PER, holding IS, contrat
   de capitalisation IS : chaque enveloppe a sa logique. Mal arbitrer, c'est
   payer plusieurs points de rendement annuel en frottement fiscal.
2. **Le coût caché du rebalancement** — un rebalancement naïf déclenche de
   l'IR/PFU sur CTO, du mark-to-market en holding IS, ou casse l'antériorité
   PEA. Un bon rebalancement se fait d'abord par les flux entrants.
3. **La conformité CIF** — DER, lettre de mission, profilage MIF II, RAA,
   journal — tout doit être produit, signé eIDAS, archivé. Aucun outil ETF
   passif ne génère ça.

**Sextant** existe pour résoudre ces trois frictions dans un seul parcours
mission, sans rupture, en local, sans appel cloud.

## Ce que Sextant fait, concrètement

- **Importe** un patrimoine réel hétérogène depuis les PDF des établissements
  (10 templates : Bourse Direct, Boursorama, Fortuneo, BNP, SG, Crédit Agricole,
  CIC/CM, Generali, Linxea, AXA) avec OCR fallback et score de confiance.
- **Diagnostique** la friction actuelle : concentration, frais courants,
  inefficience d'asset location, alertes fiscales (mark-to-market 209-0 A,
  H2O, titres UK post-Brexit, concentration PEE…), pièges MIF II.
- **Recommande** une **allocation cible** Boglehead (cœur indiciel mondial +
  poche obligataire calibrée au profil) et son **asset location optimale**
  par MILP sous contrainte fiscale (le bon ETF dans la bonne enveloppe).
- **Planifie** un **rebalancement par les flux** sur 12 mois trimestriels
  pour minimiser les ventes taxables ; ne déclenche un rebalancement par
  arbitrage que si l'écart à la cible le justifie.
- **Produit** les livrables CIF signés eIDAS : DER, lettre de mission, RAA
  MIF II, classeur PDF diagnostic, Excel de suivi, ordres CSV — tout dans
  un ZIP horodaté.
- **Trace** les hypothèses (rendements, inflation, fiscalité) avec snapshot
  SHA-256 versionné, pour défendre la mission en revue annuelle.

## Le parcours mission en 6 étapes

| # | Étape | Output | Durée |
|---|---|---|---|
| 0 | Qualification | Score 0–10 (8 questions) | 30 min |
| 1 | Onboarding | DER + LM + profilage MIF II signés | 2h |
| 2 | Diagnostic | Friction fiscale chiffrée + alertes | 4h |
| 3 | Recommandations | Allocation cible + asset location MILP | 2h |
| 4 | Plan d'action | Rebalancement par flux 12 mois | 2h |
| 5 | Livrables signés | RAA MIF II + classeur PDF eIDAS | 1h |
| 6 | Suivi annuel | Revue + delta réalisé (frais + fiscalité) | 2h/an |

Mission complète : ~4 semaines, livrables signés archivés, économies de
friction chiffrées et défendables.

## Architecture

```
src/
├── mission/           # Orchestration du cycle de vie mission (lifecycle, snapshot, ZIP)
├── import_patrimoine/ # Import PDF multi-établissements (10 templates, OCR fallback)
├── allocation/        # Allocation cible + asset location MILP sous contrainte fiscale
├── fiscalite/         # Moteur fiscal général (13 modules : IR, PFU, PS, PEA, AV...)
├── fiscalite_is/      # Brique IS : mark-to-market 209-0 A, contrat cap IS, 150-0 B ter
├── plan_action/       # Cascade trimestrielle 12 mois
├── execution/         # Screener ETF, ordres, déploiement DCA/lump
├── livrables/         # DER, LM, RAA MIF II, PDF diagnostic, Excel
├── cif/               # DER, LM, RAA, journal, signature eIDAS
├── profilage/         # Profilage MIF II
├── alertes/           # Règles d'alerte (fiscales, conformité, allocation)
├── conformite/        # Vérifications réglementaires
├── hypotheses/        # Catalogue YAML + snapshot SHA-256 versionné
├── suivi/             # Revue annuelle + delta frais/fiscalité réalisé
├── preremplissage/    # Déductions intelligentes (TMI, profil de risque, allocation)
├── validations/       # 6 règles de cohérence non bloquantes
└── ui/                # Thème Private Banking + 10 composants éditoriaux
```

## État actuel

| Composant | Statut |
|---|---|
| Import patrimoine PDF (10 templates) | ✅ Opérationnel |
| Allocation cible + asset location MILP | ✅ Opérationnel |
| Moteur fiscal général (13 modules) | ✅ Opérationnel |
| Brique fiscalité IS (MTM, cap IS, TLH) | ✅ Opérationnel |
| Plan d'exécution + screener ETF | ✅ Opérationnel |
| DER + LM + RAA MIF II signés eIDAS | ✅ Opérationnel |
| Hypothèses traçables (snapshot SHA-256) | ✅ Opérationnel |
| UX Private Banking (thème + composants) | ✅ Opérationnel |
| Bouton "Tout générer" → ZIP livrables | ✅ Opérationnel |
| Orchestration `src/mission/` complète | 🚧 Squelette, finalisation S+1 |
| Rebalancement par flux trimestriel | 🚧 Bloc B en cours |
| Modules grand public (MC, glide path, backtest) | 📦 Voir `archive/README.md` |

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

## Cas de test dogfood

Voir [`dogfood/cas_rousseau/`](dogfood/cas_rousseau/) — cas fictif complet
(famille Rousseau-Marchand, ~1,125 M€ répartis sur 5 enveloppes hétérogènes)
pour tester le parcours mission de bout en bout, avec grille de scoring sur
18 pièges et fixture YAML pour les tests de régression.

## Modules archivés

Les modules non alignés sur le parcours mission EC-CIF (Monte-Carlo, glide
path, backtest historique, 22 onglets Excel, univers 70 ETF, profils types
fictifs, pages Streamlit pédagogiques Boglehead grand public) sont conservés
dans `archive/` pour l'historique git. Voir `archive/README.md`.

## Avertissement réglementaire

Sextant produit des livrables réglementaires (DER, LM, RAA MIF II) destinés
à être signés eIDAS et utilisés en mission CIF facturée. Cet usage nécessite :

- l'inscription effective de l'utilisateur au registre ORIAS en CIF,
- une RC Pro produit couvrant l'usage de l'outil,
- un audit du moteur fiscal par un fiscaliste senior (cf.
  `docs/audit_fiscal_externe.md`, à venir).

L'outil ne se substitue ni à la responsabilité du conseiller, ni au devoir de
conseil personnalisé, ni à la vigilance MIF II.

## Crédits

- **Lucide Icons** — ISC License — https://lucide.dev
- **EB Garamond** — OFL License — Georg Duffner
- **Inter** — OFL License — Rasmus Andersson
- Philosophie d'investissement : John C. Bogle / Bogleheads community

## Licence

MIT

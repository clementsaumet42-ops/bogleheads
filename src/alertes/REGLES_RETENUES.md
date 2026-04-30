# Règles fiscales retenues pour dirigeants IS

Sur les 40 règles du moteur d'alertes, 12 sont retenues comme pertinentes
pour la cible EC + dirigeants PME avec holding à l'IS.

## Les 12 règles retenues

| # | ID règle | Description | Module source |
|---|---|---|---|
| 1 | `piege_mtm_opcvm_is` | Piège mark-to-market Art. 209-0 A CGI sur OPCVM en holding IS | `src/fiscalite/cto_is.py` |
| 2 | `contrat_cap_is_alternatif` | Contrat de capitalisation IS comme alternative au CTO IS | `src/fiscalite/contrat_cap_is.py` |
| 3 | `plafond_pea_atteint` | Plafond PEA 150 k€ atteint → basculer vers AV ou CTO | `src/fiscalite/pea.py` |
| 4 | `pea_eligible_sortie` | PEA ≥ 5 ans → sortie possible avec PS 17,2 % uniquement | `src/fiscalite/pea.py` |
| 5 | `av_8ans_abattement` | AV ≥ 8 ans → abattement annuel 4 600 € / 9 200 € exploitable | `src/fiscalite/assurance_vie.py` |
| 6 | `cehr_tranche_superieure` | CEHR sur RFR > 500 k€ → optimiser les sorties | `src/fiscalite/tmi.py` |
| 7 | `tlh_opportunite` | Tax-loss harvesting : moins-values latentes compensables | `src/fiscalite_is/tax_loss_harvesting.py` |
| 8 | `apport_cession_eligible` | Apport-cession Art. 150-0 B ter : report d'imposition possible | `src/fiscalite_is/apport_cession_150_0_B_ter.py` |
| 9 | `holding_tresorerie_excedentaire` | Trésorerie excédentaire en holding IS → allocation financière recommandée | `src/fiscalite/is_calc.py` |
| 10 | `is_taux_reduit_eligible` | Bénéfice IS ≤ 42 500 € → taux réduit 15 % applicable | `src/fiscalite/is_calc.py` |
| 11 | `liquidites_non_optimisees` | Liquidités > 20 % du patrimoine → rendement insuffisant | `src/schemas.py` |
| 12 | `der_a_renouveler` | DER > 1 an → renouvellement obligatoire MIF II | `src/cif/der.py` |

## Règles non retenues (28 règles archivées)

Les 28 règles restantes couvrent des cas spécifiques :
- Investisseurs particuliers IR (non pertinent IS)
- Profils retraite et glide path (hors cible EC)
- Pédagogie ETF et comparatifs Boglehead (hors mission)

Voir `archive/README.md` pour le contexte du pivot.

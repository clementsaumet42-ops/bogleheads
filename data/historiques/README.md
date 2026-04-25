# Données historiques

Séries de rendements mensuels totaux en EUR pour le backtest S9.

## Format

Chaque fichier CSV contient deux colonnes :
- `date` : date de fin de mois (YYYY-MM-DD)
- `rendement_total_eur` : rendement mensuel total en EUR (décimal, ex: 0.007 = 0.7%)

## Fichiers disponibles

| Fichier | Classe d'actifs | Période |
|---------|----------------|---------|
| `actions_monde_developpe.csv` | Actions monde développé (proxy MSCI World) | 2003–2024 |
| `actions_emergents.csv` | Actions marchés émergents (proxy MSCI EM) | 2003–2024 |
| `obligations_euro_agg.csv` | Obligations Euro Agrégat | 2003–2024 |
| `cash_eur.csv` | Monétaire EUR | 2003–2024 |
| `or.csv` | Or (Gold) | 2003–2024 |

## Note

Les séries sont synthétiques et générées à des fins de démonstration.
Pour des données réelles, utiliser des ETF de référence (IWDA, IEMM, IEAG, etc.)
ou configurer le fallback yfinance.

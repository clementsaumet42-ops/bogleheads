# Backtest Historique — Sprint S9

## Vue d'ensemble

Le module `src/backtest/` implémente un système de backtest mensuel pour les portefeuilles Boglehead canoniques, simulant leur comportement sur données historiques EUR (2003–2024).

## Architecture

```
src/backtest/
├── __init__.py
├── donnees_historiques.py   # Chargement des séries CSV / fallback yfinance
├── portefeuilles_bogle.py   # Définitions des 5 portefeuilles canoniques
├── metriques.py             # CAGR, Sharpe, Sortino, Calmar, MDD, Volatilité
├── frais.py                 # Modélisation des frais (TER, courtage, spread)
├── fiscalite_backtest.py    # Fiscalité (PFU, PS, optimisation enveloppes)
├── moteur_backtest.py       # Moteur de simulation mensuelle
└── comparaison.py           # Comparaison 4 modes + génération graphiques
```

## Données historiques

Les séries sont stockées dans `data/historiques/<classe>.csv` avec deux colonnes :
- `date` : fin de mois (YYYY-MM-DD)
- `rendement_total_eur` : rendement mensuel total en EUR

Classes disponibles (CSV fournis) :
- `actions_monde_developpe` — proxy MSCI World
- `actions_emergents` — proxy MSCI EM
- `obligations_euro_agg` — obligations Euro Agrégat
- `cash_eur` — monétaire EUR
- `or` — or (Gold)

Classes avec fallback yfinance si CSV absent :
- `actions_europe`, `actions_usa`
- `obligations_euro_souveraines`, `obligations_inflation_eur`
- `matieres_premieres`

## Portefeuilles Bogle disponibles

| Nom | Description | Allocations |
|-----|-------------|-------------|
| `BOGLE_2_FUNDS_70_30` | Two-fund portfolio | 70% World + 30% Euro Agg |
| `BOGLE_3_FUNDS_60_30_10` | Three-fund portfolio | 60% World + 30% Euro Agg + 10% EM |
| `BOGLE_4_FUNDS` | Four-fund français | 50% World + 20% EM + 20% Euro Agg + 10% Inflation |
| `LAZY_PERMANENT_PORTFOLIO` | Permanent Portfolio H. Browne | 25% × 4 |
| `ALL_WEATHER_RAY_DALIO` | All Weather R. Dalio | 30%/40%/15%/7.5%/7.5% |

## 4 modes de backtest

| Mode | Description |
|------|-------------|
| `brut` | Sans frais ni fiscalité |
| `net_frais` | Après TER ETF + courtage + frais enveloppe |
| `net_fiscal_cto` | Après frais + fiscalité CTO (PFU 30%) |
| `net_optimise` | Après frais + fiscalité optimisée (PEA/AV/PER) |

## Métriques calculées

- **CAGR** : Compound Annual Growth Rate
- **Volatilité annualisée** : std mensuel × √12
- **Sharpe** : (rendement excédentaire moyen annualisé) / volatilité
- **Sortino** : variante utilisant la downside deviation
- **Calmar** : CAGR / |Max Drawdown|
- **Max Drawdown** : perte maximale depuis le sommet

## Utilisation

### Lancer le backtest complet

```bash
python build_backtest.py
```

### Utilisation programmatique

```python
from src.backtest.comparaison import comparer_4_niveaux
from src.backtest.portefeuilles_bogle import BOGLE_2_FUNDS_70_30

rapport = comparer_4_niveaux(
    portefeuille=BOGLE_2_FUNDS_70_30,
    config_backtest={
        "capital_initial_eur": 100_000,
        "date_debut": "2003-01-31",
        "date_fin": "2024-12-31",
        "frais": {},
        "fiscalite": {},
    },
)
print(f"CAGR brut: {rapport.resultats['brut'].cagr:.2%}")
print(f"Impact frais: {rapport.delta_frais_bps:.1f} bps/an")
```

### Interface Streamlit

```bash
streamlit run app.py
# puis naviguer vers page 16 — Backtest
```

## Configuration

Éditer `config/backtest.yaml` pour ajuster :
- Capital initial et période
- TER par classe d'actifs
- Frais de courtage et spread
- Frais d'enveloppe (AV, PER)
- Taux de distribution (dividendes)
- Portefeuilles à analyser

## Dépendances optionnelles

```bash
pip install "bogleheads[backtest]"  # installe yfinance
```

## Avertissement

Les données historiques fournies sont synthétiques à des fins de démonstration.
Pour des backtests avec données réelles, configurer yfinance ou fournir vos propres CSV.

**Les performances passées ne préjugent pas des performances futures.**
Cet outil ne constitue pas un conseil en investissement.

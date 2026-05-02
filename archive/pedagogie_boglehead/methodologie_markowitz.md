# Méthodologie Markowitz — Sources, calibration et limites

> **Document de référence** — Sprint S11-A  
> *Outil CGP Multi-Enveloppes Boglehead FR*  
> Dernière mise à jour : 2026-04-24

---

## 1. D'où viennent les rendements espérés (μ) ?

### 1.1. Méthodologie générale

Les rendements espérés sont des **hypothèses consensuelles long terme**, agrégées à partir de quatre publications institutionnelles majeures :

| Source | Mise à jour | Lien |
|--------|-------------|------|
| **JPM Long-Term Capital Market Assumptions** | Annuelle (Jan.) | [am.jpmorgan.com](https://am.jpmorgan.com/us/en/asset-management/adv/insights/portfolio-insights/ltcma/) |
| **Vanguard Capital Markets Model (VCM)** | Annuelle (Jan.) | [advisors.vanguard.com](https://advisors.vanguard.com/iwe/pdf/ISGVEMO.pdf) |
| **Research Affiliates CMA** | Trimestrielle | [research.rafi.com](https://interactive.researchaffiliates.com/asset-allocation) |
| **BlackRock Investment Institute** | Annuelle (Déc.) | [blackrock.com](https://www.blackrock.com/corporate/insights/blackrock-investment-institute) |

Ces sources couvrent des horizons de 10 à 15 ans et expriment des rendements nominaux annualisés en USD ou en devise locale. **Une conversion en EUR est appliquée** (pas de couverture de change supposée pour les ETF UCITS domiciliés en Irlande/Luxembourg, qui maintiennent l'exposition devise).

### 1.2. Classes d'actifs et sources spécifiques

| Classe | μ retenu | Justification |
|--------|----------|---------------|
| `actions_usa` | 7,8 % | JPM LTCMA 2026 : 7,4 % · VCM 2026 : 7–9 % → centrale 7,8 % |
| `actions_dev_ex_usa` | 6,5 % | JPM : 6,0–7,5 % · RA Q1 2026 : 6,3 % → centrale 6,5 % |
| `actions_em` | 8,5 % | JPM : 8–9 % · RA prime EM ~1,5 pp → centrale 8,5 % |
| `obligations_agg_monde` | 3,0 % | JPM Global Aggregate 2,9 % → arrondi 3,0 % |
| `obligations_euro` | 2,5 % | JPM Euro Aggregate 2,5 % · OAT 10 ans France 2026 |
| `reit` | 6,0 % | **À reviewer** — valeur héritée |
| `or_matieres` | 4,0 % | **À reviewer** — valeur héritée |
| `monetaire` | 2,8 % | Taux BCE directeur moyen anticipé 2026 |
| `actions_monde_acwi` | 7,2 % | Moyenne pondérée ACWI (60 % US + 28 % dev ex-US + 12 % EM) |

⚠️ **Les valeurs REIT et or/matières premières n'ont pas de source institutionnelle vérifiée à ce stade.** Elles sont marquées `# TODO: recalibrer` dans `config/optimiseur.yaml` et doivent être révisées avec des données MSCI World Real Estate / LBMA Gold réelles.

### 1.3. Période de référence

- **Données de calibration :** 1995-01-31 → 2024-12-31
- **Nb observations mensuelles :** 360
- **Devise :** EUR (rendements nets de retenue à la source estimée)

---

## 2. D'où viennent les volatilités (σ) ?

Les volatilités annuelles sont des **estimations consensuelles institutionnelles** basées sur la formule :

```
σ_annuelle = σ_mensuelle × √12
```

Calculées sur les séries MSCI Net Total Return EUR sur la période 1995-2024, puis validées contre les publications JPM LTCMA et Vanguard VCM 2026.

| Classe | σ annuelle | Commentaire |
|--------|-----------|-------------|
| `actions_usa` | 18 % | Correspond à volatilité historique S&P 500 EUR ~17-20 % |
| `actions_dev_ex_usa` | 17 % | MSCI World ex USA EUR |
| `actions_em` | 24 % | Volatilité élevée caractéristique des marchés émergents |
| `obligations_agg_monde` | 6 % | Duration modifiée ~6 ans → sensibilité taux |
| `obligations_euro` | 5 % | Duration plus courte en euro |
| `reit` | 19 % | Proche actions, corrélation élevée avec marché |
| `or_matieres` | 20 % | Volatilité or ~15-25 % selon période |
| `monetaire` | 0,5 % | Quasi-sans risque — livret / fonds monétaire |
| `actions_monde_acwi` | 16,5 % | Diversification légèrement inférieure à World seul |

---

## 3. D'où viennent les corrélations ?

La matrice de corrélation est une **estimation long terme consensuelle**, dérivée de :

1. **Corrélations historiques** 1995-2024 sur rendements mensuels EUR (corrélation de Pearson)
2. **Validation croisée** avec les matrices publiées par JPM LTCMA 2026 et Vanguard

### Propriétés vérifiées automatiquement (`src/optimiseur/config_schemas.py`)

- **Symétrie** : ρ(A, B) = ρ(B, A) à 10⁻⁹ près
- **Diagonale** : ρ(A, A) = 1 pour toute classe A
- **Valeurs ∈ [-1, 1]**

### Points notables

| Paire | ρ | Justification |
|-------|---|---------------|
| actions_usa × actions_dev_ex_usa | 0,85 | Marchés développés très intégrés |
| actions × obligations_euro | -0,08 à -0,05 | Corrélation négative modérée (flight to quality) |
| obligations_euro × monetaire | 0,35 | Sensibilité commune aux taux courts |
| or_matieres × actions | ~0,05-0,15 | Décorrélation partielle — valeur refuge |

---

## 4. Shrinkage de Ledoit-Wolf (optionnel, désactivé par défaut)

### 4.1. Problème adressé

L'optimiseur de Markowitz est **très sensible aux erreurs d'estimation** des paramètres μ et Σ (problème dit de « garbage in, garbage out »). Avec peu d'observations et beaucoup de classes, la matrice de covariance empirique peut être singulière ou presque singulière, produisant des **poids extrêmes** ou instables.

### 4.2. Méthode Ledoit-Wolf

Le shrinkage de Ledoit-Wolf ([Ledoit & Wolf, 2004](https://doi.org/10.1016/S0047-259X(03)00096-4)) régularise la matrice de covariance en la « shrinkant » vers une cible sphérique :

```
Σ_LW = (1 - ρ) × Σ_empirique + ρ × μ_trace × I
```

où ρ est le coefficient de shrinkage optimal estimé analytiquement (formule Oracle) :

```
μ = Tr(Σ) / n
ρ = min(1, max(0, [(n-2)/n × Tr(Σ²) + Tr(Σ)²] / [(n+2) × (Tr(Σ²) - Tr(Σ)²/n)]))
```

Cette implémentation est **purement analytique** — aucune génération de données synthétiques n'est nécessaire.

### 4.3. Utilisation dans le code

```python
from src.optimiseur_allocation import optimiser_allocation_mode_a

# Désactivé par défaut (comportement actuel)
resultat = optimiser_allocation_mode_a(profil_aversion="equilibre", config=config)

# Avec shrinkage Ledoit-Wolf
resultat_shrinkage = optimiser_allocation_mode_a(
    profil_aversion="equilibre",
    config=config,
    appliquer_shrinkage=True,
    methode_shrinkage="ledoit_wolf",
)
```

### 4.4. Pourquoi pas par défaut ?

1. **Opacité** : le shrinkage modifie silencieusement la matrice — difficile à expliquer au client
2. **Calibration déjà lissée** : nos μ/σ/ρ sont déjà des estimations consensuelles (pas empiriques brutes), réduisant le besoin de régularisation
3. **Reproductibilité** : les résultats avec shrinkage dépendent de l'implémentation sklearn — risque de breaking change entre versions
4. **Tests** : les tests de rétrocompatibilité supposent résultats identiques sans shrinkage

**Activer si** :
- Instabilité numérique observée (poids > 90 % sur une seule classe)
- Mode granulaire avec 7+ classes simultanées
- Matrice quasi-singulière détectée (eigenvalue proche de 0)

---

## 5. Limites de l'optimiseur Markowitz

### 5.1. Sensibilité aux inputs (« error maximization »)

L'optimiseur Markowitz est mathématiquement exact mais **amplifie les erreurs d'estimation** de μ et Σ. Une variation de 1 pp sur un rendement espéré peut changer les poids de 10-20 pp. C'est pourquoi :
- Les intervalles de confiance IC 95 % sont fournis dans `config/optimiseur.yaml`
- Les avertissements AMF sont affichés systématiquement

### 5.2. Hypothèse de normalité

Le modèle suppose des **rendements normalement distribués**. En réalité :
- Les rendements actions présentent des **queues épaisses** (kurtosis > 3)
- Les crises (2001, 2008, 2020) génèrent des returns extrêmes sous-estimés par la normale
- Les **corrélations explosent en période de crise** (corrélations de crise >> corrélations long terme)

### 5.3. Stationnarité

L'hypothèse de stationnarité (μ, σ, ρ constants dans le temps) est **une simplification forte**. Les régimes de marché changent et les estimations historiques ne garantissent pas les paramètres futurs.

### 5.4. Horizon de placement

L'optimiseur est calibré pour un **horizon long terme (15 ans minimum)**. Pour des horizons < 5 ans, les hypothèses de rendements espérés sont moins fiables et les risques à court terme (volatilité, séquence de returns) dominent.

---

## 6. Avertissement réglementaire AMF

> *Les rendements espérés présentés dans cet outil sont des hypothèses mathématiques long terme établies à des fins d'illustration. Ils ne constituent pas une prévision ni une garantie de performance. Les performances passées ne préjugent pas des performances futures (AMF 2019-03). Tout investissement comporte un risque de perte en capital.*

---

## 7. Références

1. Markowitz, H. (1952). « Portfolio Selection ». *Journal of Finance*, 7(1), 77-91.
2. Ledoit, O. & Wolf, M. (2004). « A well-conditioned estimator for large-dimensional covariance matrices ». *Journal of Multivariate Analysis*, 88(2), 365-411.
3. JPM Asset Management. *Long-Term Capital Market Assumptions 2026*. [lien](https://am.jpmorgan.com)
4. Vanguard. *Vanguard Capital Markets Model 2026*. [lien](https://advisors.vanguard.com)
5. Research Affiliates. *Capital Market Assumptions Q1 2026*. [lien](https://interactive.researchaffiliates.com)
6. BlackRock Investment Institute. *2026 Outlook*. [lien](https://www.blackrock.com)
7. AMF. *Règlement général AMF — Article 314-31*. 2019-03.

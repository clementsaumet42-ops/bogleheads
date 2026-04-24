# Changelog LF 2026 vs LF 2025

> Récapitulatif des évolutions fiscales applicables en 2026 par rapport à 2025  
> **Sources** : Loi de Finances pour 2026 (adoptée fin 2025), LFSS 2026, BOFiP

---

## ⚠️ Avertissement

Certains taux restent à confirmer dans la LF 2026 définitive. Les valeurs marquées `_confirmer: true` dans `config/fiscalite/2026.yaml` doivent être vérifiées auprès d'un expert-comptable avant utilisation en production.

---

## 1. Prélèvements Sociaux

### 2025 → 2026

| Paramètre | LF 2025 | LF 2026 | Évolution |
|-----------|---------|---------|-----------|
| Taux total PS | 17,2% | **18,6%** ⚠️ à confirmer | +1,4 pt |
| CSG | 9,2% | **12,1%** ⚠️ | +2,9 pt |
| CRDS | 0,5% | 0,5% | = |
| Prélèvement solidarité | 7,5% | **6,0%** ⚠️ | -1,5 pt |

> **Note** : La décomposition exacte est incertaine. Le fichier `config/fiscalite/2026.yaml` et `config/fiscalite_2026.yaml` utilisent **18,6%** total pour maintenir la cohérence avec les calculs en cours. Vérifier la LFSS 2026 officielle (Art. L.136-8 CSS).

---

## 2. PFU (Flat Tax)

### 2025 → 2026

| Paramètre | LF 2025 | LF 2026 | Évolution |
|-----------|---------|---------|-----------|
| Part IR du PFU | 12,8% | 12,8% | = |
| Part PS du PFU | 17,2% | 18,6% ⚠️ | +1,4 pt |
| **Total PFU** | **30%** | **31,4%** ⚠️ | +1,4 pt |

**Art. 200 A CGI**

---

## 3. Barème IR 2026

Tranches actualisées par indexation sur l'inflation :

| Tranche | LF 2025 | LF 2026 | |
|---------|---------|---------|---|
| 0% | ≤ 11 294 € | ≤ 11 294 € | = (à confirmer) |
| 11% | 11 295 – 28 797 € | 11 295 – 28 797 € | = |
| 30% | 28 798 – 82 341 € | 28 798 – 82 341 € | = |
| 41% | 82 342 – 177 106 € | 82 342 – 177 106 € | = |
| 45% | > 177 106 € | > 177 106 € | = |

> **Note** : Indexation sur l'inflation normalement appliquée chaque année. Les bornes exactes LF 2026 doivent être confirmées à la promulgation.

**Art. 197 CGI**

---

## 4. Plafonnement du Quotient Familial

| Paramètre | LF 2025 | LF 2026 |
|-----------|---------|---------|
| Plafond par demi-part | 1 678 € | 1 791 € (à confirmer) |

**Art. 197 CGI**

---

## 5. CDHR — Contribution Différentielle sur les Hauts Revenus

**Nouveauté LF 2025, applicable à partir de 2026.**

| Paramètre | Valeur |
|-----------|--------|
| Taux minimum d'imposition garanti | 20% du RFR |
| Seuil célibataire | 250 000 € RFR |
| Seuil couple | 500 000 € RFR |

La CDHR complète la CEHR. Elle s'applique comme un **complément d'impôt** si le taux effectif (IR + PS + CEHR) est inférieur à 20%.

**Art. 224 CGI**

---

## 6. CEHR — Contribution Exceptionnelle sur les Hauts Revenus

Taux inchangés par rapport à 2025 :

| Situation | Tranche | Taux |
|-----------|---------|------|
| Célibataire | 250 001 – 500 000 € | 3% |
| Célibataire | > 500 000 € | 4% |
| Couple | 500 001 – 1 000 000 € | 3% |
| Couple | > 1 000 000 € | 4% |

**Art. 223 sexies CGI**

---

## 7. PEA / PEA-PME

### Plafonds (inchangés)

| Enveloppe | Plafond |
|-----------|---------|
| PEA | 150 000 € |
| PEA-PME | 225 000 € |
| Cumul PEA + PEA-PME | 225 000 € |

**Art. L.221-30 CMF**

---

## 8. PER — Plan d'Épargne Retraite

### PASS 2026

Le PASS (Plafond Annuel de la Sécurité Sociale) est revalorisé chaque année :

| Paramètre | 2025 | 2026 |
|-----------|------|------|
| PASS | 46 368 € | ~47 100 € (à confirmer) |
| Plafond déduction (10% PASS) | 4 637 € | ~4 710 € |

**Art. 163 quatervicies CGI**

---

## 9. IS — Impôt sur les Sociétés

### Taux (inchangés)

| Tranche | Taux |
|---------|------|
| ≤ 42 500 € | 15% (taux réduit) |
| > 42 500 € | 25% (taux normal) |

Conditions taux réduit :
- CA < 10 M€
- Capital entièrement libéré et détenu à ≥ 75% par des personnes physiques

**Art. 219 CGI**

---

## 10. MTM OPCVM en CTO IS

**Inchangé** — Art. 209-0 A CGI toujours en vigueur.

> ⚠️ **Rappel** : Les ETF (OPCVM) détenus en CTO par une société soumise à l'IS sont soumis à réévaluation mark-to-market annuelle obligatoire. Les plus-values latentes sont imposées chaque exercice même sans cession.

---

## 11. Assurance Vie

### Régime fiscal (inchangé sauf taux PS)

| Paramètre | 2025 | 2026 |
|-----------|------|------|
| Taux PS sur gains UC | 17,2% | 18,6% ⚠️ |
| PFL avant 4 ans | 35% | 35% |
| PFL 4-8 ans | 15% | 15% |
| PFL après 8 ans | 7,5% | 7,5% |
| PFU (versements post 27/09/2017, < 8 ans) | 12,8% | 12,8% |
| Abattement célibataire | 4 600 € | 4 600 € |
| Abattement couple | 9 200 € | 9 200 € |

**Art. 125-0 A CGI ; Art. 200 A CGI**

---

## 12. Contrat Capitalisation IS

### Base forfaitaire (inchangée)

```
Base imposable = 105% × TME × prime versée
```

Le TME (Taux Moyen d'Emprunt d'État) est fixé en début d'exercice. Avec des taux longs autour de 3% en 2026, la base forfaitaire représente ~3,15% de la prime — bien inférieur à la performance attendue.

**Art. 238 septies E CGI**

---

## 📋 Récapitulatif des changements majeurs

| Enveloppe | Changement 2026 |
|-----------|----------------|
| **PS / PFU** | Hausse potentielle PS 17,2% → 18,6% (+1,4 pt) ⚠️ à confirmer |
| **CDHR** | Nouvelle contribution (LF 2025), effective en 2026 |
| **Barème IR** | Indexation annuelle (bornes légèrement relevées) |
| **PASS** | Revalorisation annuelle (~+1,6% estimé) |
| **PEA/AV/IS** | Pas de changement structural |

---

## 🔗 Sources officielles

- [Code Général des Impôts (CGI)](https://www.legifrance.gouv.fr/codes/id/LEGITEXT000006069577/)
- [Code de la Sécurité Sociale (CSS)](https://www.legifrance.gouv.fr/codes/id/LEGITEXT000006073189/)
- [Code Monétaire et Financier (CMF)](https://www.legifrance.gouv.fr/codes/id/LEGITEXT000006072026/)
- [BOFiP — Bulletin Officiel des Finances Publiques](https://bofip.impots.gouv.fr/)
- [LFSS 2026](https://www.legifrance.gouv.fr/)

# Règles Fiscales — CGP Bogleheads France 2026

> **⚠️ AVERTISSEMENT LÉGAL** : Ce document est fourni à titre pédagogique uniquement.
> Il ne constitue pas un conseil en investissement ou fiscal. Les taux et règles cités
> sont à valider sur les textes officiels publiés. Consulter un professionnel agréé.

---

## Table des matières

1. [Prélèvement Forfaitaire Unique (PFU)](#1-prélèvement-forfaitaire-unique-pfu)
2. [Prélèvements Sociaux (PS)](#2-prélèvements-sociaux)
3. [Contribution Exceptionnelle sur les Hauts Revenus (CEHR)](#3-cehr)
4. [Contribution Différentielle sur les Hauts Revenus (CDHR)](#4-cdhr)
5. [Impôt sur les Sociétés (IS)](#5-impôt-sur-les-sociétés)
6. [Mark-to-Market IS — Piège art. 209-0 A CGI](#6-mark-to-market-is)
7. [Contrat de Capitalisation IS](#7-contrat-de-capitalisation-is)
8. [Fiscalité par Enveloppe](#8-fiscalité-par-enveloppe)

---

## 1. Prélèvement Forfaitaire Unique (PFU)

**Sources** : Art. 200 A CGI, LF 2018 (entrée en vigueur 1er janvier 2018), BOFiP RPPM-RCM-20-15

### Taux 2026

| Composante | Taux |
|---|---|
| Quote-part IR | 12.8 % |
| Quote-part PS | 18.6 % (À VALIDER) |
| **PFU total** | **31.4 %** |

### Champ d'application

- Plus-values de cession de valeurs mobilières (art. 150-0 A CGI)
- Dividendes d'actions
- Intérêts et produits de placement à revenu fixe
- Revenus distribués par OPCVM

### Option pour le barème progressif

Le contribuable peut **opter globalement** pour le barème de l'IR (art. 200 A 2 CGI).
Dans ce cas :
- Abattement de **40 %** sur les dividendes (art. 158-3-2° CGI)
- Déductibilité de la **CSG à 6.8 %** sur revenus de placement imposés au barème
- Intéressant si TMI < 12.8 % (tranche 0 %) — rare pour dividendes importants

### Imputation des moins-values

- Moins-values de l'année et des 10 années précédentes imputables sur les plus-values de même nature (art. 150-0 D CGI)
- ⚠️ Attention : L'option pour le barème une année ne reporte pas les moins-values des années PFU

---

## 2. Prélèvements Sociaux

**Sources** : Art. L136-1 et s. CSS, Ordonnance 96-50 du 24 janvier 1996, Art. 235 ter ZD CGI

### Décomposition 2026 — À VALIDER sur LFSS 2026

| Contribution | Taux | Base légale |
|---|---|---|
| CSG | 9.9 % | Art. L136-6 CSS |
| CRDS | 0.5 % | Ord. 96-50 |
| Prélèvement de solidarité | 7.5 % | Art. 235 ter ZD CGI |
| Contribution additionnelle | 0.7 % | **À VALIDER LFSS 2026** |
| **Total** | **18.6 %** | |

### Taux réduit PER capital

Pour la part des gains sur les versements déduits lors de la sortie en capital du PER, le taux PS applicable est de **10.3 %** (taux réduit). **À VALIDER BOFiP.**

---

## 3. CEHR

**Sources** : Art. 223 sexies CGI, BOFiP IR-IFI-CHAMP-30-20

### Tranches

| Situation | RFR | Taux |
|---|---|---|
| Célibataire | 250 001 € à 500 000 € | 3 % |
| Célibataire | > 500 000 € | 4 % (sur l'excédent) |
| Couple/PACS | 500 001 € à 1 000 000 € | 3 % |
| Couple/PACS | > 1 000 000 € | 4 % (sur l'excédent) |

### Exemple de calcul — célibataire RFR 600 000 €

```
Tranche 3 % : (500 000 - 250 000) × 3 % = 7 500 €
Tranche 4 % : (600 000 - 500 000) × 4 % = 4 000 €
CEHR total  : 11 500 €
```

---

## 4. CDHR

**Sources** : Art. 3 LF 2025 — **À VALIDER reconduite LF 2026**, BOFiP à publier

### Principe

La CDHR vise à garantir un **taux effectif minimal de 20 %** pour les contribuables dont le Revenu Fiscal de Référence (RFR) dépasse :
- 250 000 € pour un célibataire
- 500 000 € pour un couple/PACS

### Formule

```
CDHR = max(0 ; RFR × 20 % - impôts_avant_CDHR)
```

### Note

Introduite en LF 2025 et théoriquement reconduite en 2026. **À CONFIRMER** sur le texte de la LF 2026.

---

## 5. Impôt sur les Sociétés

**Sources** : Art. 219 CGI, BOFiP BIC-IS, LF 2024 (relèvement plafond taux réduit)

### Taux 2026

| Bénéfice | Taux | Condition |
|---|---|---|
| ≤ 42 500 € | 15 % (taux réduit) | PME (CA < 10 M€, capital détenu à 75 % par PP) |
| > 42 500 € | 25 % | Taux normal |

⚠️ **Note** : Le seuil de 42 500 € résulte du relèvement opéré par la LF 2024 (art. 11) du précédent seuil de 38 120 €.

---

## 6. Mark-to-Market IS

**Sources** : Art. 209-0 A CGI, BOFiP BIC-BASE-35-30

### ⚠️ PIÈGE MAJEUR pour les sociétés IS

Les OPCVM (y compris les ETF UCITS) détenus par une **société soumise à l'IS** via un compte-titres ordinaire (CTO IS) sont soumis à l'imposition **annuelle** sur la variation de valeur liquidative, **même sans cession**.

### Mécanisme

```
Base imposable année N = Valeur_liquidative_31/12/N - Valeur_liquidative_31/12/(N-1)
IS dû = base_imposable × taux_IS (si positif)
```

### Solution

Préférer le **contrat de capitalisation IS** (voir section suivante) pour les placements financiers en trésorerie de société.

---

## 7. Contrat de Capitalisation IS

**Sources** : Art. 38 sexdecies GB Annexe III CGI, BOFiP BIC-BASE-20-20

### Principe

Pour les sociétés IS, la base imposable annuelle d'un contrat de capitalisation est calculée de manière **forfaitaire** :

```
Base imposable annuelle = 105 % × TME × prime_nette
```

**Avantage** : évite le mark-to-market de l'art. 209-0 A CGI applicable aux ETF en CTO direct.

### Exemple

| Paramètre | Valeur |
|---|---|
| Prime nette versée | 100 000 € |
| TME | 3.0 % |
| Base forfaitaire | 3 150 € |
| IS estimé (25 %) | 787.50 € |

### Comparaison avec CTO IS (ETF +10 %)

| Enveloppe | Base imposable | IS (25 %) |
|---|---|---|
| CTO IS (mark-to-market) | 10 000 € | 2 500 € |
| Contrat capitalisation IS | 3 150 € | 787.50 € |
| **Économie annuelle** | **6 850 €** | **1 712.50 €** |

---

## 8. Fiscalité par Enveloppe

### CTO Personne Physique

**Base légale** : Art. 150-0 A, 200 A CGI

| Phase | Fiscalité |
|---|---|
| Entrée | Revenus nets d'impôts (aucun avantage) |
| Détention | PFU ou barème sur dividendes/coupons chaque année |
| Sortie | PFU 31.4 % sur PV réalisée |
| Moins-values | Imputables sur 10 ans |

### PEA

**Base légale** : Art. L221-30 CMF, Art. 157 bis CGI, BOFiP RPPM-RCM-40-50-50-20

| Phase | Fiscalité |
|---|---|
| Entrée | Aucun avantage |
| Détention | Capitalisation libre, aucun impôt interne |
| Sortie < 5 ans | PFU 31.4 % + clôture du plan |
| Sortie ≥ 5 ans | **IR exonéré**, PS 17.2 % (ou 18.6 % — À VALIDER) |

**Éligibilité ETF** : ETFs UCITS investis à ≥ 75 % en actions UE/EEE. Les ETFs synthétiques (swap) sur MSCI World sont éligibles si le portefeuille de substitution respecte cette règle.

### PER Individuel

**Base légale** : Ord. 2019-766, Art. L224-1 CMF, Art. 163 quatervicies CGI

| Phase | Fiscalité |
|---|---|
| Entrée | **Déductible** du revenu imposable (dans les plafonds) |
| Détention | Report d'imposition total |
| Sortie capital | IR barème (TMI) + PS 10.3 % sur gains (si déduction prise) |
| Sortie rente | IR barème après abattement 10 % |

### PEE

**Base légale** : Art. L3332-1 CT, Art. 163 bis B CGI

| Phase | Fiscalité |
|---|---|
| Abondement employeur | Exonéré IR (dans limite 8 % PASS) |
| Intéressement versé | Exonéré IR |
| Détention | Capitalisation libre |
| Sortie ≥ 5 ans | **IR exonéré sur PV**, PS 17.2 % (ou 18.6 % — À VALIDER) |

---

*Document mis à jour pour la LF/LFSS 2026. Taux marqués "À VALIDER" à confirmer sur les textes officiels publiés.*

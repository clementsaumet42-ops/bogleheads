# Guide du Moteur Fiscal — Boglehead FR 2026

> **Juridiction** : France | **Devise** : EUR | **Loi de Finances** : LF 2026  
> **Périmètre** : Fiscalité détenteur vivant — CTO, PEA, PER, Assurance Vie, Contrats capitalisation IS.  
> **Hors périmètre** : transmission, succession, donation, démembrement, Dutreil.

---

## 📦 Architecture du module

```
src/fiscalite/
├── __init__.py               # Re-exports API publique + rétrocompatibilité
├── constantes.py             # Tous les taux/seuils LF 2026
├── prelevements_sociaux.py   # PS 18.6% (CSG + CRDS + solidarité)
├── pfu.py                    # PFU 30% + CEHR + CDHR
├── cto_ir.py                 # CTO particulier (PFU ou barème)
├── cto_is.py                 # CTO société IS — MTM OPCVM (art. 209-0 A CGI)
├── contrat_cap_is.py         # Contrat de capitalisation IS (base forfaitaire)
├── pea.py                    # PEA + PEA-PME (durée, plafonds, sortie)
├── per.py                    # PERin + PERob + PERco (déduction, sortie)
├── assurance_vie.py          # AV multi-dates, multi-versements, multi-rachats
├── tmi.py                    # Barème IR 2026, quotient familial, plafonnement
├── is_calc.py                # Calcul IS (taux réduit 15% / normal 25%)
└── cascade.py                # Orchestrateur : position → ResultatFiscal
```

---

## 🔑 Modèles Pydantic

### `LigneCalcul`
```python
class LigneCalcul(BaseModel):
    libelle: str      # "Assiette imposable"
    montant: float    # 15_000.0
    formule: str      # "montant_racheté × (PV / valeur_contrat)"
    source: str       # "Art. 125-0 A CGI"
```

### `ResultatFiscal`
```python
class ResultatFiscal(BaseModel):
    montant_brut: float
    impot_ir: float
    prelevements_sociaux: float
    cehr: float
    cdhr: float
    total_impots: float
    montant_net: float
    taux_effectif: float
    cascade: list[LigneCalcul]   # détail étape par étape
    articles_cites: list[str]
    avertissements: list[str]
```

---

## 📊 Prélèvements Sociaux (PS)

**Taux 2026 : 18,6%** — Art. L.136-8 CSS ; LFSS 2026

| Composante | Taux |
|-----------|------|
| CSG | 12,1% |
| CRDS | 0,5% |
| Prélèvement de solidarité | 6,0% |
| **Total** | **18,6%** |

> ⚠️ Certaines sources évoquent un taux de 17,2% hérité de 2024. Le fichier de configuration contient le flag `_confirmer` pour les valeurs incertaines.

### Exemple de calcul

```python
from src.fiscalite import calculer_ps

result = calculer_ps(assiette=10_000.0)
# {"assiette": 10000.0, "ps": 1860.0, "net": 8140.0}
```

---

## 🏦 PFU — Flat Tax 30%

**Art. 200 A CGI**

| Composante | Taux |
|-----------|------|
| IR (PFU) | 12,8% |
| Prélèvements sociaux | 18,6% |
| **Total PFU** | **31,4%** |

### Exemple

```python
from src.fiscalite import calculer_pfu_complet

result = calculer_pfu_complet(
    gain_brut=10_000.0,
    rfr=200_000.0,
    situation="celibataire"
)
print(result.montant_net)   # 6 860 €
print(result.cascade)       # Détail ligne par ligne
```

---

## 📈 PEA / PEA-PME

**Art. L.221-30 et suivants CMF ; Art. 150-0 A CGI**

### Durées et fiscalité

| Durée | Fiscalité retrait |
|-------|------------------|
| < 2 ans | PFU 31,4% + clôture |
| 2–5 ans | PFU 31,4% + clôture |
| ≥ 5 ans | **Exonération IR + PS 18,6% sur gains uniquement** |

### Plafonds

| Enveloppe | Plafond versements |
|-----------|-------------------|
| PEA | 150 000 € |
| PEA-PME | 225 000 € |
| Cumul PEA + PEA-PME | 225 000 € |

### Cas de force majeure (retrait avant 5 ans sans clôture)
- Licenciement
- Invalidité 2e ou 3e catégorie
- Mise à la retraite anticipée
- Création ou reprise d'entreprise

### Exemple

```python
from src.fiscalite import calculer_fiscalite_retrait_pea

result = calculer_fiscalite_retrait_pea(
    gain=50_000.0,
    annees_detention=6,
    valeur_totale_pea=200_000.0
)
print(result.montant_net)           # 50 000 - (50 000 × 18.6%) = 40 700 €
print(result.articles_cites)        # ["Art. 150-0 A CGI", "Art. L.221-30 CMF"]
```

---

## 💼 PER — Plan d'Épargne Retraite

**Art. L.224-1 et suivants CMF ; Art. 163 quatervicies CGI**

### Déduction à l'entrée

Plafond = max(10% des revenus professionnels, 10% du PASS)

| Paramètre | Valeur 2026 |
|-----------|-------------|
| PASS 2026 | 47 100 € (estimation) |
| Plafond 10% PASS | 4 710 € |
| Plafond max (1 PASS) | 47 100 € |

Le plafond est reportable sur 3 ans (N-1, N-2, N-3).

### Fiscalité à la sortie

| Mode sortie | Versements déduits | Versements non déduits |
|-------------|-------------------|----------------------|
| **Capital** | IR barème sur cotisations + PFU 30% sur gains | PFU 30% sur gains seulement |
| **Rente** | IR catégorie pensions (abattement 10%) + PS | RVTO (abattement selon âge) |

### Sortie anticipée (6 cas limitatifs)
1. Achat résidence principale (1ère acquisition)
2. Invalidité du titulaire, conjoint ou enfants
3. Décès du conjoint ou partenaire PACS
4. Surendettement
5. Expiration des droits à l'assurance chômage
6. Cessation d'activité non salariée suite à liquidation judiciaire

### Exemple

```python
from src.fiscalite import calculer_fiscalite_sortie_per

result = calculer_fiscalite_sortie_per(
    montant_capital=100_000.0,
    dont_cotisations_deduites=80_000.0,
    dont_gains=20_000.0,
    tmi=0.30,
    mode_sortie="capital"
)
# IR sur 80 000 × 30% = 24 000 €
# PFU sur 20 000 × 30% = 6 000 €
# Total impôts = 30 000 €
```

---

## 🏛️ Assurance Vie — Règles multi-dates

**Art. 125-0 A CGI ; Art. 200 A CGI ; BOI-RPPM-RCM-20-10-20-50**

### Date pivot : 27 septembre 2017

La fiscalité dépend de la **date du versement** (pas de la date d'ouverture du contrat).

### Versements **avant** le 27/09/2017

| Ancienneté contrat | Fiscalité IR | PS |
|-------------------|-------------|-----|
| < 4 ans | PFL 35% ou barème IR | 18,6% |
| 4–8 ans | PFL 15% ou barème IR | 18,6% |
| > 8 ans | PFL 7,5% + abattement | 18,6% |

### Versements **après** le 27/09/2017

| Ancienneté contrat | Encours | Fiscalité IR | PS |
|-------------------|---------|-------------|-----|
| < 8 ans | — | PFU 12,8% | 18,6% |
| ≥ 8 ans | ≤ 150 k€ (célib.) | 7,5% | 18,6% |
| ≥ 8 ans | > 150 k€ | PFU 12,8% sur excédent | 18,6% |

### Abattements annuels (contrats ≥ 8 ans)
- **Célibataire** : 4 600 €/an
- **Couple** : 9 200 €/an

### Prorata plus-value
Pour un rachat partiel, seule la part de plus-value est imposable :
```
Part PV = montant_racheté × (PV_totale / valeur_totale_contrat)
```

### Exemple : contrat ouvert en 2015, versement de 2020, rachat > 8 ans

```python
from datetime import date
from src.fiscalite import ContratAV, VersementAV, RachatAV, calculer_fiscalite_rachat

contrat = ContratAV(
    date_ouverture=date(2015, 6, 1),
    assureur="AXA",
    pays="FR",
    versements=[
        VersementAV(
            date_versement=date(2020, 3, 15),
            montant=200_000.0,
            support="uc",
            plus_value_acquise=30_000.0,
        )
    ],
    rachats_passes=[],
    situation_familiale="celibataire",
)

rachat = RachatAV(
    date_rachat=date(2025, 1, 10),
    montant_rachete=50_000.0,
    option_fiscale="pfu",
    abattement_consomme_annee=0.0,
)

result = calculer_fiscalite_rachat(contrat, rachat, annee_fiscale=2025)
```

---

## 🏢 CTO Société IS — Piège MTM

**Art. 209-0 A CGI ; BOI-IS-BASE-10-20-20**

> ⚠️ **ALERTE ROUGE** : Les OPCVM (dont ETF) détenus dans un CTO à l'IS sont soumis à **réévaluation mark-to-market annuelle**. Les plus-values **latentes** sont imposées chaque année même sans cession !

### Fonctionnement MTM

1. Chaque 31/12, on calcule la valeur de marché vs le coût d'acquisition
2. La plus-value latente est intégrée dans le résultat fiscal IS
3. IS appliqué : 15% jusqu'à 42 500 € de bénéfice, 25% au-delà

### Détection automatique

```python
from src.fiscalite import detecter_piege_mtm

alerte = detecter_piege_mtm(
    position={
        "nom": "World ETF",
        "valeur_marche": 500_000.0,
        "cout_acquisition": 350_000.0,
        "type_instrument": "opcvm_actions",
        "pourcentage_actions": 0.95,  # > 90% → MTM obligatoire
    },
    regime_detenteur="IS"
)
# alerte["type"] == "MTM_OPCVM_IS"
# alerte["is_latent"] == 37_500.0  (IS 25% sur 150k PV latente)
```

### Alternative : Contrat de capitalisation IS

Le contrat de capitalisation IS utilise une **base forfaitaire** (art. 238 septies E CGI) :
```
Base imposable = 105% × TME × prime versée
```
Avec un TME de 3%, l'imposition annuelle est ~3,15% de la prime, indépendamment des performances réelles — avantage considérable si le portefeuille performe bien.

---

## 🏗️ Contrat Capitalisation IS

**Art. 238 septies E CGI ; BOI-BIC-PDSTK-10-20-70-30**

```python
from src.fiscalite import calculer_base_taxable_contrat_cap_is

# Base forfaitaire annuelle
base = calculer_base_taxable_contrat_cap_is(
    prime=1_000_000.0,
    tme=0.030,        # TME à la souscription
    params={}         # non utilisé (pour compatibilité)
)
# base == 1.05 × 0.030 × 1_000_000 = 31_500 €
# IS 15% sur 31_500 = 4_725 €/an (soit 0.47% de la prime)
```

**À la cession** : régularisation par la différence entre PV réelle et sommes déjà imposées forfaitairement.

---

## 📉 CEHR — Contribution Exceptionnelle Hauts Revenus

**Art. 223 sexies CGI**

| Situation | RFR | Taux CEHR |
|-----------|-----|-----------|
| Célibataire | 250 001 – 500 000 € | 3% |
| Célibataire | > 500 000 € | 4% |
| Couple | 500 001 – 1 000 000 € | 3% |
| Couple | > 1 000 000 € | 4% |

### Exemple

```python
from src.fiscalite import calculer_cehr

cehr = calculer_cehr(rfr=350_000.0, situation="celibataire")
# cehr == (350_000 - 250_000) × 3% = 3_000 €
```

---

## 🛡️ CDHR — Contribution Différentielle Hauts Revenus

**Art. 224 CGI (LF 2025, applicable en 2026)**

Assure un **taux minimum d'imposition de 20%** sur le RFR pour les foyers dont le RFR > 250 000 € (célibataire) ou 500 000 € (couple).

```python
from src.fiscalite import calculer_cdhr

cdhr = calculer_cdhr(
    rfr=300_000.0,
    impot_total_existant=40_000.0,  # IR + PS + CEHR déjà calculés
    situation="celibataire"
)
# Taux effectif actuel = 40 000 / 300 000 = 13.3%
# CDHR = (20% - 13.3%) × 300 000 = 20 100 €
```

---

## 🧮 Barème IR 2026 + Quotient Familial

**Art. 197 CGI**

### Tranches 2026

| Revenu imposable (1 part) | Taux |
|--------------------------|------|
| Jusqu'à 11 294 € | 0% |
| 11 295 € – 28 797 € | 11% |
| 28 798 € – 82 341 € | 30% |
| 82 342 € – 177 106 € | 41% |
| Au-delà de 177 106 € | 45% |

### Quotient familial

```python
from src.fiscalite import calculer_tmi, calculer_ir_complet

# TMI pour un célibataire avec 80 000 € de revenu imposable
tmi = calculer_tmi(revenu_net_imposable=80_000.0, nb_parts=1.0)
# tmi == 0.30 (tranche 30%)

# IR complet avec quotient familial
ir = calculer_ir_complet(
    revenu_net_imposable=120_000.0,
    nb_parts=2.5,      # couple + 3 enfants
    situation="couple"
)
```

---

## 🎯 Orchestrateur Cascade

L'API unifiée pour tous les calculs fiscaux :

```python
from src.fiscalite import calculer_fiscalite_operation

result = calculer_fiscalite_operation(
    operation={
        "type": "vente_cto",
        "gain_brut": 50_000.0,
        "rfr": 180_000.0,
        "situation": "celibataire",
        "option_fiscale": "pfu",
    },
    profil={},
    annee_fiscale=2026
)

print(f"Net après impôts : {result.montant_net:.2f} €")
print(f"Taux effectif : {result.taux_effectif:.1%}")
print("\nCascade de calcul :")
for ligne in result.cascade:
    print(f"  {ligne.libelle:30s} {ligne.montant:10.2f} €  [{ligne.source}]")
```

---

## 📚 Sources réglementaires

| Module | Article principal | Source secondaire |
|--------|------------------|-------------------|
| PS | Art. L.136-8 CSS | LFSS 2026 |
| PFU | Art. 200 A CGI | BOFiP RPPM-RCM |
| CEHR | Art. 223 sexies CGI | — |
| CDHR | Art. 224 CGI | LF 2025 |
| PEA | Art. L.221-30 CMF | Art. 150-0 A CGI |
| PER | Art. L.224-1 CMF | Art. 163 quatervicies CGI |
| AV | Art. 125-0 A CGI | BOI-RPPM-RCM-20-10-20-50 |
| Contrat cap IS | Art. 238 septies E CGI | BOI-BIC-PDSTK-10-20-70-30 |
| CTO IS MTM | Art. 209-0 A CGI | BOI-IS-BASE-10-20-20 |
| IS | Art. 219 CGI | — |
| Barème IR | Art. 197 CGI | — |

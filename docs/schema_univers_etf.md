# Schéma `univers_etf.yaml` — Documentation

## Vue d'ensemble

Le fichier `config/univers_etf.yaml` constitue le référentiel central de tous les ETF disponibles dans le moteur Boglehead FR. Il contient **70 ETF** couvrant toutes les classes d'actifs pertinentes pour un portefeuille Boglehead en France.

**Principe de modularité** : ajouter, modifier ou supprimer un ETF ne doit jamais casser le moteur Python. Tous les nouveaux champs sont **optionnels** côté moteur (lus via `.get(champ, valeur_defaut)`).

---

## Champs du schéma

### Champs identifiants

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `isin` | `string` | ✅ | Code ISIN à 12 caractères (ISO 6166). Doit passer la validation Luhn. |
| `ticker` | `string` | ✅ | Code mnémonique court (ex: `CW8`, `IWDA`). |
| `nom` | `string` | ✅ | Nom complet de l'ETF. |
| `emetteur` | `string` | ✅ | Nom de la société de gestion (ex: `Amundi`, `iShares (BlackRock)`). |

### Classification

| Champ | Type | Requis | Valeurs possibles | Description |
|-------|------|--------|-------------------|-------------|
| `classe_actifs` | `string` | ✅ | `Actions`, `Obligations`, `Or`, `Matières premières`, `Immobilier`, `Monétaire`, `Diversifiants`, `Thématiques` | Classe d'actifs principale. |
| `sous_classe` | `string` | ❌ | libre | Sous-catégorie (ex: `Monde développé`, `USA S&P 500`). |
| `domicile` | `string` | ✅ | `France`, `Irlande`, `Luxembourg`, `Allemagne`, … | Pays de domiciliation de l'ETF (important pour l'éligibilité PEA). |

### Caractéristiques financières

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `ter` | `float` | ✅ | Total Expense Ratio (frais annuels). Exprimé en décimal, ex: `0.0020` = 0,20%. |
| `devise` | `string` | ✅ | Devise de cotation/référence (`EUR`, `USD`, `HKD`, …). |
| `capitalisant` | `bool` | ✅ | `true` = accumulation (réinvestissement auto), `false` = distribution. |
| `eur_hedged` | `bool` | ✅ | `true` si l'ETF est couvert contre le risque de change EUR. |

### Méthode de réplication

| Champ | Type | Requis | Valeurs autorisées | Description |
|-------|------|--------|-------------------|-------------|
| `methode_replication` | `string` | ✅ | `physique`, `synthetique_swap`, `synthetique_swap_unfunded`, `physique_optimisee` | Mode de réplication de l'indice. **Critère structurant pour l'éligibilité PEA.** |

**Règle PEA et réplication** :
- ETF actions **hors UE/EEE** (USA, monde, émergents, Japon...) → PEA éligible **uniquement** si `synthetique_swap` ou `synthetique_swap_unfunded`
- ETF actions **européennes** (domicile UE/EEE) → PEA éligible même avec `physique` (les actions sous-jacentes sont déjà UE/EEE)
- ETF obligations, or, matières premières, immobilier → PEA **jamais** éligible

### Documentation réglementaire

| Champ | Type | Requis | Description |
|-------|------|--------|-------------|
| `url_dic_kid` | `string \| null` | ✅ | URL officielle du Document d'Informations Clés (DIC/KID) sur le site de l'émetteur. `null` si non trouvé. **Ne jamais fabriquer une URL.** |
| `date_verification_dic` | `string` | ✅ | Date ISO 8601 de la dernière vérification (ex: `"2026-04-22"`). |
| `notes_verification` | `string` | ❌ | Note libre sur les points à vérifier manuellement (ISIN, DIC, éligibilité…). |

### Éligibilité par enveloppe

Le champ `eligibilite` est un dictionnaire de booléens :

```yaml
eligibilite:
  PEA: bool          # Plan d'Épargne en Actions
  PER: bool          # Plan d'Épargne Retraite
  PEE: bool          # Plan d'Épargne Entreprise
  CTO_perso: bool    # Compte-Titres Ordinaire personnel
  CTO_IS: bool       # CTO dans une holding IS
  Contrat_Cap_IS:    # Contrat de capitalisation IS (holding)
  AV_UC: bool        # Unité de Compte d'Assurance-Vie (NOUVEAU)
```

**Règles de cohérence** :

| Condition | Règle |
|-----------|-------|
| `classe_actifs` ∈ {`Obligations`, `Or`, `Matières premières`, `Immobilier`} | `PEA: false` obligatoire |
| `PEA: true` | `domicile` doit être dans l'UE/EEE |
| `AV_UC: false` | `contrats_av_reference` doit être `[]` |
| ETF actions hors UE + `PEA: true` | `methode_replication` doit être `synthetique_swap` ou `synthetique_swap_unfunded` |

### Assurance-Vie

| Champ | Type | Requis | Défaut | Description |
|-------|------|--------|--------|-------------|
| `eligibilite.AV_UC` | `bool` | ✅ | `false` | Éligible en Unité de Compte d'Assurance-Vie. Dépend du contrat. |
| `contrats_av_reference` | `list[string]` | ✅ | `[]` | Contrats AV où cet ETF est disponible (best-effort). Doit être vide si `AV_UC: false`. |

**Contrats de référence** (non exhaustif) :
- `"Linxea Spirit 2"` — ETF core (Amundi, iShares, Vanguard, Xtrackers)
- `"Lucya Cardif"` — large univers (~2300 UC)

### Frais

| Champ | Type | Requis | Défaut | Description |
|-------|------|--------|--------|-------------|
| `frais_entree_typique_pct` | `float` | ✅ | `0.0` | Frais d'entrée typiques chez un courtier en ligne (souvent 0%). |

### Annotations libres

| Champ | Type | Description |
|-------|------|-------------|
| `notes` | `string` | Notes générales sur l'ETF (usage, particularités). |
| `notes_verification` | `string` | Points à vérifier manuellement avant utilisation en production. |

---

## Exemple : ajouter un nouvel ETF

Voici comment ajouter l'ETF **HSBC MSCI World UCITS ETF** au fichier :

```yaml
- isin: "IE00B4X9L533"              # Vérifier sur JustETF ou HSBC
  ticker: "HMWO"
  nom: "HSBC MSCI World UCITS ETF (Acc)"
  emetteur: "HSBC AM"
  classe_actifs: "Actions"
  sous_classe: "Monde développé"
  ter: 0.0015                        # 0,15% — vérifier DIC
  devise: "USD"
  domicile: "Irlande"
  capitalisant: true
  eur_hedged: false
  methode_replication: "physique"    # Réplication physique → PEA: false
  url_dic_kid: null                  # À sourcer sur https://www.assetmanagement.hsbc.fr
  date_verification_dic: "2026-04-22"
  eligibilite:
    PEA: false                       # Physique + monde → non éligible PEA
    PER: true
    PEE: false
    CTO_perso: true
    CTO_IS: true
    Contrat_Cap_IS: true
    AV_UC: true
  contrats_av_reference:
    - "Linxea Spirit 2"
  frais_entree_typique_pct: 0.0
  notes: "Alternative compétitive à IWDA — TER 0,15%, réplication physique."
```

**Étapes à suivre** :
1. Trouver l'ISIN sur [JustETF](https://www.justetf.com/fr/), [Morningstar](https://www.morningstar.fr/) ou le site de l'émetteur
2. Vérifier le DIC/KID sur le site officiel → renseigner `url_dic_kid`
3. Déterminer `methode_replication` → déduire l'éligibilité PEA
4. Lancer les tests : `pytest tests/test_univers_etf.py`
5. Corriger les éventuelles erreurs signalées

---

## Classes d'actifs couvertes

| Classe | Exemples |
|--------|---------|
| Actions — Monde développé | CW8 (Amundi), IWDA (iShares), VWCE (Vanguard), XMWO (Xtrackers) |
| Actions — USA | CSP1 (iShares), LYPS (Amundi/Lyxor) |
| Actions — Europe | EXSA (iShares), C50 (Amundi EMU) |
| Actions — Émergents | IEEM (iShares), PAEEM (Amundi PEA) |
| Actions — Facteurs | IWVL (Value), IWQU (Quality), IWMO (Momentum), MVOL (Min Vol) |
| Obligations souveraines EUR | GOVS, IBCI, IBCM, IBCL, IBCX |
| Obligations corporate EUR | IEAA, IHYG, XZEB |
| Obligations monde | AGGH, XBAE, IBTM |
| Obligations inflation | ITPS (TIPS), C40 (OATi) |
| Obligations émergentes | SEML, SEMB |
| Immobilier (REITs) | IWDP, EPRE, XREA |
| Or physique | GOLD, IGLN, XGLD |
| Matières premières | CMOD, LYTR |
| Monétaire EUR | CSH, XEON |
| Thématiques | IH20 (Eau), INRG (Propre), IHCG (Santé), WTAI (IA) |
| ESG/ISR | SUWU (SRI Monde), LCUI (Paris Aligned) |

---

## Règles de validation automatisées

Le fichier `tests/test_univers_etf.py` valide automatiquement :

- **ISIN** : format (12 chars, 2 lettres pays + 9 alphanums + 1 check digit) et checksum Luhn
- **Unicité** : pas de doublon ISIN
- **PEA/classe** : aucun ETF Obligations/Or/Matières premières/Immobilier avec `PEA: true`
- **PEA/domicile** : domicile UE/EEE obligatoire si `PEA: true`
- **DIC** : champ `url_dic_kid` présent (URL ou `null`, jamais absent)
- **Schéma minimum** : tous les champs obligatoires présents
- **Méthode réplication** : valeur dans la liste autorisée
- **Cohérence AV** : `contrats_av_reference` vide si `AV_UC: false`
- **LU0378818131** : présence de l'ETF Xtrackers MSCI World 1C obligatoire

```bash
# Lancer les tests de validation ETF
pytest tests/test_univers_etf.py -v

# Lancer tous les tests
pytest tests/ -v
```

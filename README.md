# 🏦 Bogleheads CGP — Outil de Gestion Patrimoniale Indicielle France

Outil complet d'aide à la décision pour Conseillers en Gestion de Patrimoine (CGP)
suivant l'approche **Bogleheads** (gestion indicielle passive, low-cost, long terme).

Génère un classeur Excel interactif avec 8 feuilles couvrant la fiscalité 2026,
les enveloppes d'investissement, l'allocation d'actifs, l'asset location et le rebalancement.

---

## 🎯 Fonctionnalités

| Feuille | Description |
|---------|-------------|
| **Paramètres_Client** | Saisie âge, TMI, RFR, horizon, patrimoine — dropdowns validés |
| **Paramètres_Fiscalité_2026** | PFU, PS, CEHR, CDHR, IS avec sources CGI/BOFiP |
| **Enveloppes** | Synthèse fiscale des 6 enveloppes (CTO, PEA, PER, PEE, Capi IS) |
| **Univers_ETF** | ~25 ETFs Boglehead avec éligibilités par enveloppe |
| **Allocation_Cible** | Règle âge-en-obligations + profils prudent/équilibré/dynamique |
| **Asset_Location_Matrice** | Matrice ETF × Enveloppe, cellules grisées si non éligible, Solveur Excel |
| **Rebalancement** | Bandes de tolérance ±5 % ou Larry Swedroe, coût fiscal arbitrage |
| **Reporting_Client** | Synthèse globale + valeur ajoutée fiscale vs scénario CTO naïf |

---

## 📋 Prérequis

- **Python 3.11+**
- `pip` (gestionnaire de paquets Python)

---

## 🚀 Installation

```bash
# Cloner le dépôt
git clone https://github.com/clementsaumet42-ops/bogleheads.git
cd bogleheads

# Installer les dépendances
pip install -r requirements.txt
```

---

## ▶️ Utilisation

### Générer le classeur Excel

```bash
python build_excel.py
```

Le fichier est généré dans `output/portefeuille_bogleheads.xlsx`.

### Lancer les tests

```bash
pytest tests/ -v
```

---

## 📂 Structure du projet

```
bogleheads/
├── config/
│   ├── fiscalite_2026.yaml   # Taux fiscaux France 2026 (LF 2026)
│   ├── enveloppes.yaml       # 6 enveloppes : CTO, PEA, PER, PEE, Capi IS, CTO IS
│   └── univers_etf.yaml      # ~25 ETFs Bogleheads avec ISIN et éligibilités
├── src/
│   ├── fiscalite.py          # Calculs PFU, CEHR, CDHR, IS, mark-to-market
│   ├── enveloppes.py         # Dataclasses enveloppes
│   ├── allocation.py         # Allocation cible + règle âge-en-obligations
│   ├── asset_location.py     # Priorités enveloppe par classe d'actifs
│   ├── rebalancement.py      # Bandes tolérance + recommandations
│   └── excel_builder.py      # Constructeur classeur (8 feuilles)
├── tests/
│   └── test_fiscalite.py     # Tests pytest — calculs fiscaux
├── docs/
│   ├── regles_fiscales.md    # Référentiel fiscal avec sources légales
│   └── architecture.md       # Architecture technique
├── output/                   # Fichiers Excel générés (gitignorés)
├── build_excel.py            # Point d'entrée principal
└── requirements.txt
```

---

## ⚙️ Configuration

### Modifier les taux fiscaux

Éditer `config/fiscalite_2026.yaml` :

```yaml
pfu:
  taux_total: 0.314   # Modifier ici si LF 2027 change le PFU

tme: 0.030            # Taux Moyen des Emprunts d'État — actualiser chaque année
```

### Ajouter un ETF

Éditer `config/univers_etf.yaml` :

```yaml
- isin: IE00XXXXXXXX
  ticker: MYETF
  nom: "Mon Nouvel ETF UCITS"
  emetteur: Amundi
  classe_actifs: Actions Monde
  ter: 0.0015
  devise: EUR
  domicile: Irlande
  type: capitalisant
  eligibilite:
    pea: false
    per: true
    pee: false
    cto: true
    pea_pme: false
```

### Modifier une enveloppe

Éditer `config/enveloppes.yaml` — chaque enveloppe a un `id` unique
(`cto_perso`, `cto_is`, `contrat_capi_is`, `pea`, `per`, `pee`).

---

## 🧪 Tests

```bash
# Tous les tests
pytest tests/ -v

# Tests rapides (sans verbosité)
pytest tests/

# Test d'un cas spécifique
pytest tests/test_fiscalite.py::TestPFU::test_pfu_10000 -v
```

### Tests couverts

| Test | Vérification |
|------|-------------|
| `test_pfu_10000` | PFU 31.4 % sur 10 000 € = 3 140 € |
| `test_cehr_600000_celibataire` | CEHR = 7 500 € + 4 000 € = 11 500 € |
| `test_is_50000` | IS = 6 375 € + 1 875 € = 8 250 € |
| `test_mark_to_market_5pct` | Base imposable = 5 000 € sans cession |
| `test_contrat_cap_is_base` | Base forfaitaire = 3 150 € (TME 3 %) |
| `test_cdhr_plancher_20pct` | CDHR = 20 000 € pour garantir 20 % |

---

## 📖 Documentation fiscale

Voir `docs/regles_fiscales.md` pour le détail des règles fiscales avec leurs sources légales.

---

## ⚠️ Avertissement légal

> Les informations et calculs fournis par cet outil sont **indicatifs et pédagogiques**.
> Ils **ne constituent pas** un conseil en investissement, fiscal ou juridique.
> Certains taux sont marqués "**À VALIDER**" — ils doivent être confirmés sur les textes
> officiels publiés (LF, LFSS, CGI, BOFiP).
>
> Consulter un professionnel agréé (CGP, expert-comptable, avocat fiscaliste) avant
> toute décision patrimoniale.

---

## 📄 Licence

MIT — Usage libre avec attribution.

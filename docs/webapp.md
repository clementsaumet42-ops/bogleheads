# 🌐 Webapp Streamlit — Guide utilisateur

## Introduction

La webapp Boglehead FR est une interface web interactive construite avec Streamlit au-dessus
de toute la logique métier S1–S3. Elle permet à un CGP de démontrer l'outil à un client
sans avoir besoin d'un terminal.

## Installation et lancement

```bash
# Installation des dépendances web
pip install -e ".[web,optim]"

# Lancement
streamlit run app.py
# ou
./run_app.sh
```

L'app est accessible sur http://localhost:8501

## Architecture des pages

```
🏠 Accueil → 👤 Profil → 🎯 Allocation → 🏦 Asset Loc → 📈 Monte-Carlo → 🔄 Rebal → 📥 Exports
```

---

## Guide page par page

### 🏠 Page 1 — Accueil

**Objectif :** présentation de l'outil et navigation.

- 3 KPIs : nombre de profils types / enveloppes fiscales / ETF disponibles
- Description des 6 modules fonctionnels
- Bouton "Charger un profil client" → redirection page Profil

**Ce que vous voyez :**
```
KPIs :  👤 6 profils   🏦 6 enveloppes   📊 70 ETF

[ Charger un profil client → ]
```

---

### 👤 Page 2 — Profil client

**Objectif :** charger ou créer un profil client, stocker en session.

#### Option A — Profil type YAML
1. Sélectionnez un profil dans la liste déroulante (6 profils fictifs)
2. Aperçu : âge, TMI, patrimoine, allocation Boglehead
3. Cliquez "✅ Charger ce profil" → validation Pydantic automatique

#### Option B — Profil custom
1. Remplissez le formulaire (nom, âge, TMI, patrimoine, épargne, horizon)
2. Ajustez les sliders d'allocation cible (somme = 100 %)
3. Cochez les enveloppes disponibles et renseignez les encours
4. Cliquez "✅ Valider le profil"

**Stockage :** le profil est sauvegardé dans `st.session_state["profil_actif"]`
et persiste entre toutes les pages.

---

### 🎯 Page 3 — Allocation cible

**Objectif :** calculer l'allocation optimale Markowitz et visualiser.

1. **Sliders de contraintes** (recalcul automatique) :
   - Exposition USA max (%)
   - Exposition marchés émergents max (%)
   - Profil d'aversion au risque (défensif / équilibré / dynamique / agressif)

2. **KPIs résultats** :
   - Rendement attendu annuel
   - Volatilité annuelle
   - Ratio de Sharpe
   - Statut (optimal / fallback)

3. **Visualisations** :
   - Camembert Plotly interactif (clic pour isoler une classe)
   - Tableau poids × montants estimés

4. **Sauvegarde** : cliquez "Recalculer et sauvegarder" pour stocker dans
   `st.session_state["resultat_optim"]` (réutilisé par les pages suivantes).

---

### 🏦 Page 4 — Asset Location

**Objectif :** ventiler l'allocation cible par enveloppe fiscale (MILP).

1. Le calcul reprend automatiquement le profil en session
2. **KPIs comparaison** :
   - Coût annuel optimisé (€/an)
   - Coût annuel naïf — AV gestion pilotée (~2,3% tout compris)
   - Économie annuelle réalisée

3. **Heatmap** : matrice classes d'actifs × enveloppes avec montants
   - Intensité = montant placé
   - Survol = détail classe / enveloppe / montant

4. **Tableau détaillé** : poids et montants par ligne de ventilation

> **Note :** si PuLP est installé (`pip install -e ".[optim]"`), la résolution
> MILP exacte est utilisée. Sinon, fallback heuristique Boglehead.

---

### 📈 Page 5 — Projection Monte-Carlo

**Objectif :** simuler l'évolution du patrimoine sur 5 à 40 ans.

1. **Paramètres** (sliders interactifs) :
   - Capital initial (€) — pré-rempli depuis le profil
   - Versement mensuel (€) — converti en annuel pour la simulation
   - Horizon en années (5–40)
   - Objectif patrimonial (€)
   - Nombre de simulations (1 000 / 2 000 / 5 000 / 10 000)

2. **KPIs résultats** :
   - Capital médian final (€)
   - P10 — scénario pessimiste bas
   - P90 — scénario optimiste haut
   - Probabilité d'atteindre l'objectif (si défini)

3. **Fan chart** Plotly interactif :
   - Bande grisée P10–P90
   - Courbe bleue médiane
   - Ligne rouge pointillée = objectif (si défini)
   - Survol = valeur précise par année

> L'allocation utilisée vient de `st.session_state["resultat_optim"]`
> ou de l'allocation Boglehead du profil si non calculée.

---

### 🔄 Page 6 — Rebalancement

**Objectif :** générer un plan de rebalancement chiffré.

#### Mode "Par flux"
- Réoriente les versements vers les classes sous-pondérées
- Aucune vente → aucune fiscalité
- Tableau des montants orientés par classe

#### Mode "Optimal MILP"
- Cascade 3 étapes fiscalement optimisée :

  **Étape 1 — Arbitrages gratuits**
  - Arbitrages intra-enveloppe (PEA, PER, AV, Contrat Cap IS)
  - Coût fiscal = 0 €

  **Étape 2 — Flux entrants**
  - Réorientation des versements mensuels
  - Coût fiscal = 0 €

  **Étape 3 — Ventes optimisées**
  - Cascade : AV abattement → PEA PS 17,2% → CTO CMP/FIFO
  - Tax-loss harvesting automatique (compensation PV/MV)
  - Tableau : ETF / enveloppe / montant / PV / coût fiscal / méthode

> **Note :** l'étape 3 nécessite des positions détaillées dans le profil
> (`positions_detaillees`). Les profils types YAML incluent des positions d'exemple.

---

### 📥 Page 7 — Téléchargements

**Objectif :** générer et télécharger les rapports Excel et PDF.

#### Rapport Excel (22 onglets)
1. Cliquez "⚙️ Générer le fichier Excel" (~15–30s)
2. Une fois généré : "⬇️ Télécharger le fichier Excel"
3. Le fichier est mis en cache dans `st.session_state["excel_bytes"]`

#### Rapport PDF client (13 pages)
1. Cliquez "⚙️ Générer le rapport PDF" (~15–30s)
2. Une fois généré : "⬇️ Télécharger le rapport PDF"
3. Aperçu inline dans l'interface (iframe base64)
4. Le fichier est mis en cache dans `st.session_state["pdf_bytes"]`

---

## Gestion de l'état (session_state)

| Clé | Type | Contenu |
|---|---|---|
| `profil_actif` | `dict` | Profil Pydantic sérialisé (by_alias=True) |
| `profil_source` | `"yaml"` \| `"custom"` | Source du profil |
| `resultat_optim` | `dict` | Résultat `optimiser_portefeuille_complet()` |
| `resultat_mc` | `dict` | Résultat de la projection Monte-Carlo |
| `pdf_bytes` | `bytes` | PDF généré (cache) |
| `excel_bytes` | `bytes` | Excel généré (cache) |

**Réinitialisation :** bouton "🔄 Réinitialiser" dans la sidebar.

---

## Configuration

### Thème (.streamlit/config.toml)

```toml
[theme]
primaryColor = "#1a4d8f"      # Bleu cabinet
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f5f7fa"
textColor = "#333333"
font = "sans serif"
```

### Variables d'environnement

Aucune variable d'environnement n'est requise. Tous les fichiers de configuration
sont dans `config/` et chargés automatiquement.

---

## Déploiement

### Docker

```bash
docker build -t boglehead-fr .
docker run -p 8501:8501 boglehead-fr
```

### Streamlit Community Cloud

1. Forker le dépôt
2. Connecter sur [share.streamlit.io](https://share.streamlit.io)
3. Sélectionner `app.py` comme point d'entrée
4. Ajouter `packages.txt` si besoin de dépendances système

### Fly.io / Render

Utiliser le `Dockerfile` fourni à la racine du projet.

---

## Architecture technique

```
app.py                    ← Point d'entrée Streamlit
pages/
  1_🏠_Accueil.py         ← KPIs + navigation
  2_👤_Profil.py          ← Formulaire + validation Pydantic
  3_🎯_Allocation.py      ← Markowitz + sliders contraintes
  4_🏦_Asset_Location.py  ← MILP + heatmap
  5_📈_Monte_Carlo.py     ← Simulation + fan chart
  6_🔄_Rebalancement.py   ← Cascade fiscale 3 étapes
  7_📥_Exports.py         ← Excel + PDF
src/ui/
  __init__.py             ← Exports publics
  formatters.py           ← format_euro(), format_pct(), format_kpi()
  charts.py               ← camembert_allocation(), fan_chart_mc(), heatmap_asset_location()
.streamlit/
  config.toml             ← Thème palette cabinet
```

**Règle d'or :** `src/ui/` ne contient **aucune logique métier**.
Toutes les fonctions de calcul viennent de `src/` (optimiseur, projection, rebalancement).

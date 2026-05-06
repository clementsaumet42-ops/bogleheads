# Charte Graphique — Cabinet Saumet Patrimoine

Révision S19 — Avril 2026

---

## 1. Philosophie visuelle

Esthétique éditoriale, sobre, intemporelle. Référence : Edmond de Rothschild, Pictet, Lombard Odier.

**Niveau d'audace : Classique (style Rothschild)**
Bleu nuit + or, serif éditorial assumé, pas austère.

---

## 2. Palette officielle

| Variable CSS | Couleur HEX | Usage |
|---|---|---|
| `--bleu-nuit` | `#0B1929` | Titres, en-têtes, fond page de garde PDF |
| `--bleu-profond` | `#16263F` | Variations, hover boutons primaires |
| `--ivoire` | `#F5F1EA` | Fond principal de l'application |
| `--blanc-casse` | `#FAF7F2` | Alternance tableaux, fond cartes KPI |
| `--or-vieilli` | `#8B6F47` | Accents, traits, hover, icônes actives |
| `--or-clair` | `#B8946A` | Variations or, hover doux |
| `--ardoise` | `#2C2C2C` | Corps de texte principal |
| `--ardoise-claire` | `#5A5A5A` | Texte secondaire, labels, captions |
| `--rouge-bordeaux` | `#6B1E2C` | Alertes danger uniquement |
| `--vert-foret` | `#2D4A3E` | Validations discrètes |

### Équivalents Python (`src/ui/theme.py`)

```python
BLEU_NUIT = "#0B1929"
BLEU_PROFOND = "#16263F"
IVOIRE = "#F5F1EA"
BLANC_CASSE = "#FAF7F2"
OR_VIEILLI = "#8B6F47"
OR_CLAIR = "#B8946A"
ARDOISE = "#2C2C2C"
ARDOISE_CLAIRE = "#5A5A5A"
ROUGE_BORDEAUX = "#6B1E2C"
VERT_FORET = "#2D4A3E"
```

---

## 3. Typographie

### Polices

| Rôle | Police | Fallback |
|---|---|---|
| Titres | EB Garamond (Google Fonts) | Georgia, "Times New Roman", serif |
| Corps | Inter (Google Fonts) | system-ui, sans-serif |
| Chiffres tabulaires | EB Garamond avec `font-feature-settings: "tnum"` | Georgia, serif |

### Tailles et graisses

| Élément | Taille | Graisse | Police |
|---|---|---|---|
| Titre page (h1) | 2.25rem | 700 | EB Garamond |
| Section (h2) | 1.75rem | 600 | EB Garamond |
| Sous-section (h3) | 1.35rem | 600 | EB Garamond |
| Corps de texte | 15px | 400 | Inter |
| Label KPI | 0.688rem | 400 | Inter italic |
| Valeur KPI | 2rem | 700 | EB Garamond |
| Caption/note | 0.8rem | 400 | Inter |

### Espacement

- `line-height` corps : 1.7
- `letter-spacing` labels : 0.08em
- Padding sections minimum : 2rem
- Séparateurs horizontaux : 0.5px, couleur `--or-vieilli` à 35% d'opacité

---

## 4. Composants UI (`src/ui/components.py`)

### `titre_page(titre, sous_titre?, icone?)`
Titre éditorial EB Garamond 36px avec séparateur or. Le sous-titre s'affiche en italique ardoise claire.

### `kpi_card(label, valeur, variation?, tendance?)`
Carte chiffre fond blanc cassé, bordure or 0.5px. Valeur en EB Garamond 32px bleu nuit, label en Inter italic 11px.

### `tableau_elegant(df, colonnes_chiffrees?)`
Tableau avec en-têtes bleu nuit/ivoire, alternance ivoire/blanc cassé, chiffres en EB Garamond tabulaire.

### `bouton_principal(label, key, icone_lucide?)`
Fond bleu nuit, texte ivoire, bordure or 1px. Hover : fond bleu profond, texte or clair.

### `bouton_secondaire(label, key, icone_lucide?)`
Transparent, bordure ardoise fine. Hover : bordure or, texte or.

### `panneau_avertissement(severity, titre, description)`
Filet gauche 4px coloré. `"info"` = or, `"warning"` = ardoise claire, `"danger"` = rouge bordeaux. Fond blanc cassé.

### `section(titre, contenu_callback, separateur_or?)`
Section éditoriale avec filet or fin sous le titre EB Garamond.

### `icone_lucide(nom, taille?, couleur?)`
Charge un SVG Lucide depuis `assets/icons/{nom}.svg` et l'injecte inline.

### `lettrine(texte, taille?)`
Première lettre en EB Garamond 64px bleu nuit (style éditorial classique).

### `monogramme_html(taille?)`
Renvoie le SVG du monogramme cabinet dimensionné.

---

## 5. Monogramme (`assets/monogramme.svg`)

Initiale "S" (Saumet) en EB Garamond Bold dans un cartouche ovale or vieilli (1.5pt) sur fond bleu nuit.

Variantes disponibles :
- `assets/monogramme.svg` — couleur (or sur bleu nuit)
- `assets/monogramme_or.svg` — or sur transparent
- `assets/monogramme_blanc.svg` — blanc sur transparent

L'EC peut remplacer ce monogramme par son logo via `config/pdf_cabinet.yaml` (champ `cabinet.logo_path`).

---

## 6. Icônes Lucide (`assets/icons/`)

Icônes SVG monochromes, stroke 1.5px, couleur par défaut `--ardoise-claire`, hover `--or-vieilli`.

### Catalogue

| Icône | Fichier | Usage |
|---|---|---|
| `chevron-right` | `chevron-right.svg` | Navigation, liens |
| `check` | `check.svg` | Validation, succès |
| `alert-circle` | `alert-circle.svg` | Alertes, avertissements |
| `info` | `info.svg` | Informations, suggestions |
| `download` | `download.svg` | Téléchargement, génération |
| `file-text` | `file-text.svg` | Documents, hypothèses |
| `users` | `users.svg` | Clients, profils |
| `briefcase` | `briefcase.svg` | Mission, EC |
| `trending-up` | `trending-up.svg` | Projection, performance |
| `pie-chart` | `pie-chart.svg` | Allocation, répartition |
| `calendar` | `calendar.svg` | Dates, planning |
| `clock` | `clock.svg` | Durée, horizon |
| `archive` | `archive.svg` | Archivage, historique |
| `external-link` | `external-link.svg` | Liens externes |
| `settings` | `settings.svg` | Configuration |
| `arrow-right` | `arrow-right.svg` | Navigation, suite |
| `eye` | `eye.svg` | Visualisation, aperçu |
| `printer` | `printer.svg` | Impression, export PDF |

**Licence** : Lucide Icons — ISC License (libre d'utilisation commerciale)

---

## 7. Palette PDF (`src/pdf_builder.py`)

| Variable | HEX | Usage |
|---|---|---|
| `_PRIMARY` | `#0B1929` | En-têtes tableaux, titres |
| `_ACCENT` | `#8B6F47` | Traits, séparateurs |
| `_NEUTRAL` | `#2C2C2C` | Corps de texte |
| `_LIGHT_GREY` | `#F5F1EA` | Fond lignes impaires (ivoire) |
| `_MED_GREY` | `#FAF7F2` | Fond lignes paires (blanc cassé) |

### Graphiques matplotlib

- **Camembert** : dégradé bleu nuit → or → ardoise (5 tons)
- **Monte-Carlo** : médiane en bleu nuit, P10/P90 en ardoise claire à 25% de remplissage
- Fond des graphiques : `#FAF7F2` (blanc cassé)
- Pas de grille, axes fins en ardoise claire 0.5pt, bords droit et haut masqués

---

## 8. Règles "Ne jamais utiliser"

### Emojis dans l'UI

Aucun emoji dans :
- Pages Streamlit (fichiers `pages/*.py`)
- Modules UI (`src/ui/*.py`)
- PDF généré (`src/pdf_builder.py`)
- En-têtes Excel visibles

Les emojis sont **autorisés** dans :
- Commentaires de code (`# ...`)
- Docstrings (entre `"""..."""`)
- Messages git et CHANGELOG
- `page_icon=` dans `st.set_page_config()` (icône de l'onglet navigateur)

### Couleurs hors palette

Ne pas utiliser de couleurs non définies dans la palette officielle ci-dessus.
En particulier, éviter les bleus Streamlit par défaut (`#1f77b4`), rouges vifs, verts fluorescents.

### Polices hors charte

Utiliser exclusivement **EB Garamond** (titres) et **Inter** (corps).
Ne pas introduire de nouvelles polices sans mise à jour de cette charte.

### Styles Streamlit par défaut

Les styles par défaut de Streamlit (fond blanc, boutons bleus) sont surchargés par le CSS injecté
via `injecter_css()` dans `src/ui/theme.py`. Cette fonction doit être appelée au début de chaque page.

---

## 9. Exemples avant/après (S19)

### Titre de page

**Avant (S18)** :
```python
st.title("📈 Projection Monte-Carlo")
```

**Après (S19)** :
```python
from src.ui.components import titre_page
titre_page("Projection long terme", sous_titre="5 000 simulations Monte-Carlo", icone="trending-up")
```

### Alerte

**Avant (S18)** :
```python
st.warning("⚠️ Aucun profil chargé.")
```

**Après (S19)** :
```python
from src.ui.components import panneau_avertissement
panneau_avertissement("warning", "Profil manquant", "Veuillez d'abord configurer un profil client.")
```

### Bouton

**Avant (S18)** :
```python
if st.button("🚀 Tout générer", type="primary"):
    ...
```

**Après (S19)** :
```python
from src.ui.components import bouton_principal
if bouton_principal("Générer le dossier complet", key="btn_tout_generer", icone_lucide="download"):
    ...
```

---

## 10. Crédits et licences

- **EB Garamond** — Georg Duffner — [OFL (Open Font License)](https://fonts.google.com/specimen/EB+Garamond)
- **Inter** — Rasmus Andersson — [OFL (Open Font License)](https://fonts.google.com/specimen/Inter)
- **Lucide Icons** — Lucide Contributors — [ISC License](https://lucide.dev/license)

---

*Dernière mise à jour : Sprint S19 — Avril 2026*

# Changelog

Toutes les modifications notables de ce projet sont documentées ici.

Format : [Semantic Versioning](https://semver.org/lang/fr/) — [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/)

---

## [1.0.0] — Sprint S19 — UX Private Banking (refonte visuelle haut de gamme)

### Ajouté

#### Lot A — Système de thème
- `.streamlit/config.toml` : palette Private Banking (or vieilli, ivoire, ardoise, bleu nuit)
- `src/ui/theme.py` : constantes de palette Python + fonction `injecter_css()` (CSS global ~200 lignes)
  - Imports Google Fonts EB Garamond + Inter via @import
  - Override composants Streamlit (boutons, headers, tableaux, sidebar, expanders, metric, alertes)
  - Fallback Georgia/"Times New Roman" + system-ui si Google Fonts hors ligne

#### Lot B — Composants UI réutilisables
- `src/ui/components.py` : 10 composants éditoriaux
  - `titre_page()` — EB Garamond 36px + séparateur or
  - `kpi_card()` — valeur serif 32px, fond blanc cassé, bordure or fine
  - `tableau_elegant()` — alternance ivoire/blanc cassé, chiffres EB Garamond tabulaire
  - `bouton_principal()` — bleu nuit + or, hover bleu profond
  - `bouton_secondaire()` — transparent + ardoise, hover or
  - `panneau_avertissement()` — filet gauche 4px coloré (or/ardoise/bordeaux)
  - `section()` — section éditoriale avec séparateur or
  - `icone_lucide()` — SVG Lucide inline depuis `assets/icons/`
  - `lettrine()` — première lettre EB Garamond 64px
  - `monogramme_html()` — SVG monogramme cabinet dimensionné

#### Lot C — Refonte pages Streamlit
- 26 pages `pages/` refaites : zéro emoji dans l'UI rendue
- Appel `injecter_css()` ajouté sur chaque page
- `st.title()` / `st.header()` remplacés par `titre_page()` / `section()` sur les pages principales

#### Lot D — Refonte PDF
- `src/pdf_builder.py` : palette Private Banking (bleu nuit `#0B1929`, or `#8B6F47`)
- Tableaux : en-têtes bleu nuit/ivoire, alternance ivoire/blanc cassé, filets or 0.25pt
- Camembert : palette dégradée bleu nuit → or → ardoise
- Monte-Carlo : médiane bleu nuit, P10/P90 ardoise claire 25%, pas de grille, axes fins ardoise
- Suppression emojis dans le texte PDF (alertes, cabinets, ETFs)

#### Lot E — Ressources statiques
- `assets/monogramme.svg` — initiale "S" or sur bleu nuit, cartouche ovale
- `assets/monogramme_or.svg` — variante or sur transparent
- `assets/monogramme_blanc.svg` — variante blanc sur transparent
- `assets/icons/` — 18 icônes Lucide SVG (stroke 1.5px) : chevron-right, check, alert-circle, info, download, file-text, users, briefcase, trending-up, pie-chart, calendar, clock, archive, external-link, settings, arrow-right, eye, printer

#### Lot F — Documentation
- `docs/charte-graphique.md` : palette, typographie, composants, icônes, règles
- `README.md` : mention charte graphique + crédits Lucide/EB Garamond/Inter
- `CHANGELOG.md` : entrée S19

#### Tests
- `tests/test_ui_components.py` : `injecter_css()` + 15 composants testés avec mock Streamlit
- `tests/test_no_emoji_in_ui.py` : scanner récursif pages/ et src/ui/, whitelist page_icon= et commentaires
- `tests/test_pdf_visual_regression.py` : palette `_PRIMARY`/`_ACCENT`, nombre de pages, nom client, patrimoine total

### Modifié
- Zéro modification de logique métier (fiscalite, allocation, optimiseur, audit, conformite, execution, hypotheses, mission)

### Crédits
- **Lucide Icons** — ISC License — https://lucide.dev
- **EB Garamond** — OFL License — Georg Duffner
- **Inter** — OFL License — Rasmus Andersson

---


### Ajouté

#### Lot A — Auto-save session (`src/mission/autosave.py`)
- `activer_autosave(mission_id, intervalle_secondes)` : flush du `session_state` dans la mission toutes les N secondes (opt-in, toggle dans sidebar)
- `restaurer_session(mission_id)` : charge le snapshot persisté au démarrage
- `sauvegarder_immediatement(mission_id, cle, valeur)` : force le flush d'une clé critique
- Filtre automatique des types non sérialisables (DataFrames → `list[dict]`, objets complexes → ignorés avec log)
- Champ `session_state_snapshot: dict | None` ajouté à `EtatMission` (rétro-compatible — missions S16 sans ce champ chargées sans erreur)
- Toggle "💾 Auto-save activé" dans la sidebar de `pages/00_Mission_CGP.py` (off par défaut)

#### Lot B — Préremplissage intelligent (`src/preremplissage/`)
- `deduire_tmi(revenu_net_annuel, situation, nb_enfants)` : déduit la TMI depuis le revenu via `src/fiscalite/tmi` (aucune duplication)
- `deduire_profil_risque(age, horizon_annees)` : règle 100-âge (<30→dynamique, 30-50→équilibré, 50-65→prudent, >65→conservateur) + affinage horizon court
- `deduire_allocation_cible(profil_risque, horizon_annees)` : allocation indicative par profil
- `deduire_esperance_vie(age, sexe)` : tables INSEE 2023 avec interpolation linéaire
- `Suggestion` dataclass : toutes les suggestions marquées 💡, `modifiable=True`, jamais imposées
- API unifiée `src/preremplissage/suggestions.py`

#### Lot C — Validations croisées (`src/validations/coherence.py`)
- `Avertissement` dataclass : `cle`, `severity` (info/warning/danger), `titre`, `description`, `suggestion`, `pages_concernees`
- `valider_coherence(profil)` : lance les 6 règles, jamais bloquant
- **Règle 1** : Patrimoine total ≠ somme enveloppes (>1% écart) → warning
- **Règle 2** : TMI incohérente avec RFR déclaré → warning + suggestion correction
- **Règle 3** : Profil dynamique avec horizon < 5 ans → warning
- **Règle 4** : Âge ≥ objectif retraite → info
- **Règle 5** : Capital < frais courtage × 10 → warning
- **Règle 6** : >80% monétaire avec horizon >10 ans → warning rendement réel négatif
- Section "⚠️ Avertissements de cohérence" dans `pages/00_Mission_CGP.py`

#### Lot D — Bouton "🚀 Tout générer" (`pages/00_Mission_CGP.py`)
- Section "🚀 Tout générer" en bas de la page Mission CGP
- Vérifie les 5 étapes obligatoires (profil_saisi, profilage_mif, allocation_cible, asset_location, plan_execution)
- Génère séquentiellement avec `st.progress` : récap mission PDF, snapshot hypothèses S17, PDF client, Excel, ordres CSV
- Archive tout dans `output/missions/{mission_id}/{YYYYMMDD-HHMMSS}.zip`
- Bouton "📥 Télécharger l'archive complète"
- Marque `livrables_pdf_excel` comme ✅ dans le checklist S16
- Réutilise `generer_pdf()`, `generer_excel()`, `_generer_pdf_recap()` sans aucune duplication

### Tests
- `tests/test_autosave.py` : round-trip session_state, filtrage types, restauration, rétro-compatibilité S16
- `tests/test_preremplissage.py` : chaque règle de déduction + API Suggestion
- `tests/test_coherence.py` : chaque règle déclenche / ne déclenche pas selon inputs
- `tests/test_tout_generer.py` : orchestration mockée + vérification ZIP

### Contraintes respectées
- ❌ Aucun nouveau moteur métier
- ❌ `fiscalite/*`, `allocation.py`, `optimiseur*`, `audit/alertes/*`, `conformite/*`, `src/execution/*`, `src/hypotheses/*` (S17) non modifiés
- ✅ Auto-save opt-in (toggle off par défaut)
- ✅ Préremplissages toujours marqués 💡 et modifiables
- ✅ Validations non bloquantes (warning, jamais error)
- ✅ Rétro-compatibilité S16 (lectures tolérantes champ `session_state_snapshot`)

---

## [0.8.0] — Sprint S17 — Hypothèses traçables

- `src/hypotheses/` : Source, Hypothese, catalogue YAML, snapshot SHA-256, versionnage/diff
- `config/hypotheses.yaml` : registre peuplé de toutes les hypothèses du PDF
- PDF page 17 : annexe "Hypothèses retenues & sources"
- `pages/23_Hypotheses.py` : vue de consultation lecture seule

---

## [0.7.0] — Sprint S16 — Page Mission CGP unifiée

- `src/mission/` : EtatMission, checklist 13 étapes, progression, widgets
- `pages/00_Mission_CGP.py` : fil conducteur avec checklist visuelle et export PDF récap

---

## [0.6.0] — Sprint S15 — Plan d'exécution

- `src/execution/` : screener ETF, ordres, déploiement DCA/lump, calendrier Gantt
- `pages/22_Plan_Execution.py` : page plan d'exécution

---

## [0.5.0] — Sprints S1–S14

- Moteurs : allocation, asset location, Monte-Carlo, rebalancement MILP, fiscalité complète, CIF/NRP, conformité, audit, catalogue ETF, brokers/assureurs/teneurs PER

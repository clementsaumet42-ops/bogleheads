# Changelog

Toutes les modifications notables de ce projet sont documentées ici.

Format : [Semantic Versioning](https://semver.org/lang/fr/) — [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/)

---

## [0.9.0] — Sprint S18 — Densification UX

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

# Changelog

Toutes les modifications notables de ce projet sont documentées ici.

Format : [Semantic Versioning](https://semver.org/lang/fr/) — [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/)

---

## [1.0.0] — Sprint S20 — Import patrimoine depuis PDF

### Ajouté

#### Lot A — Pipeline extraction `src/import_patrimoine/`
- `extracteur.py` — orchestrateur complet : pdfplumber (texte natif) → OCR Tesseract (fallback scan) → détection émetteur → template → lignes Pydantic
- `modele.py` — modèles Pydantic v2 : `LignePatrimoine` (ISIN, nom, valorisation, enveloppe, broker, confiance…), `ImportPDF`, `ResultatExtraction`
- `confiance.py` — score 0-100 par ligne : template+40, ISIN valide+25, valorisation parsée+20, enveloppe identifiée+10, texte natif+5
- `detecteur_emetteur.py` — détection signature émetteur par regex sur en-têtes + scan global PDF
- `parseur_template.py` — lecture YAML template + application règles tableau/regex/hybride avec `_parse_montant` robuste
- `audit.py` — journal d'audit append-only JSON dans `data/missions/{id}/audit.json`
- `ocr.py` — OCR via pytesseract + pdf2image avec fallback gracieux si Tesseract absent

#### Lot B — 10 templates YAML `src/import_patrimoine/templates/`
| Template | Émetteur | Type |
|---|---|---|
| `bourse_direct.yaml` | Bourse Direct | Courtier |
| `boursorama.yaml` | Boursorama | Banque/courtier |
| `fortuneo.yaml` | Fortuneo | Banque/courtier |
| `bnp_paribas.yaml` | BNP Paribas | Banque détail |
| `societe_generale.yaml` | Société Générale | Banque détail |
| `credit_agricole.yaml` | Crédit Agricole | Banque détail (toutes caisses) |
| `cic_cm.yaml` | CIC / Crédit Mutuel | Banque |
| `generali.yaml` | Generali | Assureur AV |
| `linxea.yaml` | Linxea | Courtier AV (Spirit, Avenir, Zen) |
| `axa.yaml` | AXA | Assureur AV |

#### Lot C — OCR Tesseract
- `src/import_patrimoine/ocr.py` : `extraire_via_ocr()`, `detecter_pdf_scanne()` (seuil < 100 caractères)
- Fallback gracieux : si Tesseract absent → message clair, pas de crash
- CI `.github/workflows/ci.yml` : step `Install Tesseract` (tesseract-ocr + tesseract-ocr-fra + poppler-utils)

#### Lot D — UI Streamlit `pages/24_Import_Patrimoine.py`
- Upload multi-PDF (`st.file_uploader`)
- Extraction automatique avec barre de progression
- Tableau éditable (`st.data_editor`) : statut couleur (Vert/Orange/Rouge), ISIN, nom, valorisation, enveloppe, broker, confiance
- Validation conservatrice ligne par ligne (checkbox individuel)
- Boutons : "Valider toutes les lignes vertes" / "Valider toutes (avec confirmation)"
- Bouton "Importer dans la mission" → merge dans `EtatMission.imports_patrimoine`
- Historique des imports par mission
- Zéro emoji dans l'UI (charte S19)

#### Lot E — Intégration mission S16
- `EtatMission.imports_patrimoine: list[dict]` (default `[]`) — rétro-compatible
- `EtatMission.ajouter_import(import_pdf: ImportPDF)` — méthode d'ajout
- `to_dict()` / `from_dict()` mis à jour (missions existantes chargées sans erreur)
- Étape optionnelle `patrimoine_importe` ajoutée à `ETAPES_CANONIQUES` (phase RDV1, obligatoire=False)

### Tests
- `tests/test_extracteur.py` : extraction texte, détection scan, roundtrip Pydantic
- `tests/test_detecteur_emetteur.py` : détection pour chaque template synthétique + inconnu
- `tests/test_confiance.py` : score haute confiance ≥ 90, score OCR sans template < 30
- `tests/test_ocr.py` : fallback gracieux (3 cas), skip si Tesseract installé
- `tests/test_import_mission_integration.py` : merge, sérialisation, rétro-compatibilité, audit append-only

### Infrastructure
- `.gitignore` : `data/missions/*/imports/` ajouté (PDF jamais commités)
- `pyproject.toml` : dépendances optionnelles `[pdf]` : `pdfplumber>=0.10`, `pytesseract>=0.3`, `pdf2image>=1.17`
- `docs/import_patrimoine.md` : guide calibration templates YAML

### Contraintes respectées
- ❌ Aucune logique métier touchée (fiscalité, allocation, optimiseur, audit, conformité, exécution, hypothèses, profilage, asset_location, rebalancement)
- ❌ Aucun appel cloud/LLM — 100% local
- ❌ Aucun merge silencieux — validation ligne par ligne obligatoire
- ❌ Aucun emoji dans l'UI
- ✅ Rétro-compatibilité S16/S17/S18 totale
- ✅ Tests métier existants 100% verts

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
